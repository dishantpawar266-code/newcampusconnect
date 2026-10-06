import os
import json
import uuid
from datetime import datetime, timezone
from functools import wraps
import io

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, abort, send_file
)
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Notice, Assignment, UploadedFile, Note, Doubt, Quiz, QuizResult, Conversation, Message, StudySession, Task, ExamReminder

load_dotenv()

# ---------------------------------------------------------------------------
# App Initialisation
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-prod")

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    database_url = "sqlite:///campus_connect.db"
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEPARTMENTS = [
    "Artificial Intelligence & Machine Learning (AIML)",
    "Computer Science Engineering (Data Science)",
    "Artificial Intelligence & Data Science (AIDS)",
    "Electronics & Telecommunication Engineering (ENTC)",
    "Information Technology (IT)",
    "Mechanical Engineering",
    "Electrical Engineering",
]

ALLOWED_FILE_EXTENSIONS = {"txt", "ppt", "pptx", "jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_MB = 10

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_FILE_EXTENSIONS

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "uid" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_current_user():
    if "uid" not in session:
        return None
    if session["uid"] == "__admin__":
        return {"id": "__admin__", "name": "Administrator", "role": "admin"}
    
    user = User.query.get(session["uid"])
    if user:
        u_dict = {
            "id": user.id,
            "uid": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "department": user.department,
            "departments": json.loads(user.departments) if user.departments else [],
            "roll_number": user.roll_number,
            "year": user.year,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "designation": user.designation,
            "club_name": user.club_name,
            "club_category": user.club_category,
            "description": user.description,
            "is_active": user.is_active
        }
        return u_dict
    return None

def firebase_web_config():
    return {}

@app.context_processor
def inject_globals():
    return {
        "current_user": get_current_user(),
        "firebase_config": firebase_web_config(),
        "departments": DEPARTMENTS,
    }

# ===========================================================================
# PUBLIC ROUTES
# ===========================================================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if "uid" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        return _handle_register(request.form)
    return render_template("auth/register.html", departments=DEPARTMENTS)

def _handle_register(form):
    role = form.get("role", "student").strip().lower()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "").strip()
    confirm_password = form.get("confirm_password", "").strip()
    name = form.get("name", "").strip()

    if not all([role, email, password, name]):
        flash("All fields are required.", "danger")
        return render_template("auth/register.html", departments=DEPARTMENTS)
    if password != confirm_password:
        flash("Passwords do not match.", "danger")
        return render_template("auth/register.html", departments=DEPARTMENTS)
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return render_template("auth/register.html", departments=DEPARTMENTS)
    if role not in ("student", "faculty", "club"):
        flash("Invalid role.", "danger")
        return render_template("auth/register.html", departments=DEPARTMENTS)

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash("An account with this email already exists.", "danger")
        return render_template("auth/register.html", departments=DEPARTMENTS)

    try:
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            name=name,
            role=role,
            is_active=True
        )

        if role == "student":
            user.department = form.get("department", "")
            user.roll_number = form.get("roll_number", "").strip()
            user.year = form.get("year", "")
        elif role == "faculty":
            departments = form.getlist("department")
            user.departments = json.dumps(departments)
            user.designation = form.get("designation", "").strip()
        elif role == "club":
            user.club_name = form.get("club_name", name).strip()
            user.club_category = form.get("club_category", "").strip()
            user.description = form.get("description", "").strip()

        db.session.add(user)
        db.session.commit()

        session["uid"] = user.id
        session["role"] = role
        session["name"] = name
        flash(f"Welcome to Campus Connect 3.0, {name}! Your account has been created.", "success")
        return redirect(url_for("dashboard"))

    except Exception as e:
        app.logger.error(f"Registration error: {e}")
        db.session.rollback()
        flash("Registration failed. Please try again.", "danger")

    return render_template("auth/register.html", departments=DEPARTMENTS)

@app.route("/login", methods=["GET", "POST"])
def login():
    if "uid" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        return _handle_login(request.form)
    return render_template("auth/login.html")

def _handle_login(form):
    email = form.get("email", "").strip().lower()
    password = form.get("password", "").strip()
    admin_code = form.get("admin_code", "").strip()

    if admin_code:
        return _handle_admin_login(admin_code)

    if not email or not password:
        flash("Email and password are required.", "danger")
        return render_template("auth/login.html")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        flash("Invalid email or password.", "danger")
        return render_template("auth/login.html")
    
    if not user.is_active:
        flash("Your account has been disabled. Contact admin.", "danger")
        return render_template("auth/login.html")

    session["uid"] = user.id
    session["role"] = user.role
    session["name"] = user.name
    flash(f"Welcome back, {user.name}!", "success")
    return redirect(url_for("dashboard"))

def _handle_admin_login(code):
    expected = os.environ.get("ADMIN_SECRET_CODE", "")
    if not expected:
        flash("Admin access not configured.", "danger")
        return render_template("auth/login.html")
    if code == expected:
        session["uid"] = "__admin__"
        session["role"] = "admin"
        session["name"] = "Administrator"
        return redirect(url_for("admin_dashboard"))
    else:
        flash("Invalid access code.", "danger")
    return render_template("auth/login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

# ===========================================================================
# FILES (Replacing Firebase Storage)
# ===========================================================================

@app.route("/file/<file_id>")
def serve_file(file_id):
    file_record = UploadedFile.query.get(file_id)
    if not file_record:
        abort(404)
    return send_file(
        io.BytesIO(file_record.data),
        mimetype=file_record.content_type,
        as_attachment=False,
        download_name=file_record.filename
    )

# ===========================================================================
# DASHBOARD
# ===========================================================================

@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    
    uid = session["uid"]
    stats = {}
    try:
        notices = Notice.query.order_by(Notice.created_at.desc()).limit(5).all()
        stats["recent_notices"] = [{"id": d.id, "title": d.title, "content": d.content, "department": d.department, "author_name": d.author_name, "created_at": d.created_at.isoformat() if d.created_at else ""} for d in notices]
        
        assignments = Assignment.query.order_by(Assignment.created_at.desc()).limit(5).all()
        stats["recent_assignments"] = [{"id": d.id, "title": d.title, "description": d.description, "deadline": d.deadline, "department": d.department, "subject": d.subject, "author_name": d.author_name, "created_at": d.created_at.isoformat() if d.created_at else ""} for d in assignments]
        
        tasks = Task.query.filter_by(user_uid=uid).order_by(Task.created_at.desc()).all()
        stats["tasks"] = [{"id": t.id, "title": t.title, "subject": t.subject, "due_date": t.due_date, "priority": t.priority, "is_completed": t.is_completed} for t in tasks]
        
        exams = ExamReminder.query.filter_by(user_uid=uid).order_by(ExamReminder.exam_date).all()
        stats["exams"] = [{"id": e.id, "subject": e.subject, "exam_date": e.exam_date, "exam_time": e.exam_time} for e in exams]
        
        study_sessions = StudySession.query.filter_by(user_uid=uid).all()
        stats["study_time_seconds"] = sum([s.duration_seconds for s in study_sessions])

    except Exception as e:
        app.logger.error(f"Dashboard stats error: {e}")
        stats["recent_notices"] = []
        stats["recent_assignments"] = []
        stats["tasks"] = []
        stats["exams"] = []
        stats["study_time_seconds"] = 0
        
    return render_template("dashboard.html", stats=stats)

# ===========================================================================
# PLANNER / TASKS
# ===========================================================================

@app.route("/planner")
@login_required
def planner():
    uid = session["uid"]
    tasks = Task.query.filter_by(user_uid=uid).order_by(Task.created_at.desc()).all()
    tasks_data = [{"id": t.id, "title": t.title, "subject": t.subject, "description": t.description, "due_date": t.due_date, "priority": t.priority, "est_time": t.est_time, "is_completed": t.is_completed} for t in tasks]
    return render_template("planner.html", tasks=tasks_data)

@app.route("/api/tasks", methods=["POST"])
@login_required
def create_task():
    uid = session["uid"]
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Title required"})
    task = Task(
        user_uid=uid,
        title=title,
        subject=data.get("subject", ""),
        description=data.get("description", ""),
        due_date=data.get("due_date", ""),
        priority=data.get("priority", "Medium"),
        est_time=data.get("est_time", "")
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/tasks/<task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    task = Task.query.get(task_id)
    if task and task.user_uid == session["uid"]:
        task.is_completed = not task.is_completed
        task.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({"ok": True, "is_completed": task.is_completed})
    return jsonify({"ok": False})

@app.route("/api/tasks/<task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    task = Task.query.get(task_id)
    if task and task.user_uid == session["uid"]:
        db.session.delete(task)
        db.session.commit()
        return jsonify({"ok": True})
    return jsonify({"ok": False})

# ===========================================================================
# EXAM REMINDERS
# ===========================================================================

@app.route("/exams")
@login_required
def exams():
    uid = session["uid"]
    exams = ExamReminder.query.filter_by(user_uid=uid).order_by(ExamReminder.exam_date).all()
    exams_data = [{"id": e.id, "subject": e.subject, "exam_date": e.exam_date, "exam_time": e.exam_time, "description": e.description} for e in exams]
    return render_template("exams.html", exams=exams_data)

@app.route("/api/exams", methods=["POST"])
@login_required
def create_exam():
    uid = session["uid"]
    data = request.get_json(silent=True) or {}
    subject = data.get("subject", "").strip()
    exam_date = data.get("exam_date", "").strip()
    if not subject or not exam_date:
        return jsonify({"ok": False, "error": "Subject and Date required"})
    exam = ExamReminder(
        user_uid=uid,
        subject=subject,
        exam_date=exam_date,
        exam_time=data.get("exam_time", ""),
        description=data.get("description", "")
    )
    db.session.add(exam)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/exams/<exam_id>", methods=["DELETE"])
@login_required
def delete_exam(exam_id):
    exam = ExamReminder.query.get(exam_id)
    if exam and exam.user_uid == session["uid"]:
        db.session.delete(exam)
        db.session.commit()
        return jsonify({"ok": True})
    return jsonify({"ok": False})


# ===========================================================================
# PROFILE
# ===========================================================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    uid = session["uid"]
    if request.method == "POST":
        user = User.query.get(uid)
        role = session.get("role")
        user.bio = request.form.get("bio", "").strip()
        user.name = request.form.get("name", "").strip()
        
        if role == "student":
            user.department = request.form.get("department", "")
            user.roll_number = request.form.get("roll_number", "").strip()
            user.year = request.form.get("year", "")
        elif role == "faculty":
            user.departments = json.dumps(request.form.getlist("department"))
            user.designation = request.form.get("designation", "").strip()
        elif role == "club":
            user.club_category = request.form.get("club_category", "").strip()
            user.description = request.form.get("description", "").strip()
            
        db.session.commit()
        session["name"] = user.name
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))
        
    user = get_current_user()
    return render_template("profile.html", user=user, departments=DEPARTMENTS)

# ===========================================================================
# NOTICES
# ===========================================================================

@app.route("/notices")
@login_required
def notices():
    dept_filter = request.args.get("department", "")
    query = Notice.query.order_by(Notice.created_at.desc())
    if dept_filter:
        query = query.filter_by(department=dept_filter)
    
    docs = query.all()
    items = [{"id": d.id, "title": d.title, "content": d.content, "department": d.department, "author_name": d.author_name, "author_uid": d.author_uid, "created_at": d.created_at.isoformat() if d.created_at else ""} for d in docs]
    return render_template("notices.html", notices=items, departments=DEPARTMENTS)

@app.route("/notices/create", methods=["GET", "POST"])
@role_required("faculty", "club")
def create_notice():
    if request.method == "POST":
        uid = session["uid"]
        user = get_current_user()
        
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Title and content are required.", "danger")
            return render_template("notices_form.html", departments=DEPARTMENTS)
            
        notice = Notice(
            title=title,
            content=content,
            department=request.form.get("department", ""),
            author_uid=uid,
            author_name=user.get("name", "Unknown") if user else "Unknown",
            author_role=session.get("role"),
            category="club" if session.get("role") == "club" else "academic"
        )
        db.session.add(notice)
        db.session.commit()
        flash("Notice published successfully.", "success")
        return redirect(url_for("notices"))
    return render_template("notices_form.html", departments=DEPARTMENTS)

@app.route("/notices/<notice_id>/edit", methods=["GET", "POST"])
@role_required("faculty", "club")
def edit_notice(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    if notice.author_uid != session["uid"]:
        flash("You can only edit your own notices.", "danger")
        return redirect(url_for("notices"))
        
    if request.method == "POST":
        notice.title = request.form.get("title", "").strip()
        notice.content = request.form.get("content", "").strip()
        notice.department = request.form.get("department", "")
        notice.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash("Notice updated.", "success")
        return redirect(url_for("notices"))
        
    notice_dict = {"id": notice.id, "title": notice.title, "content": notice.content, "department": notice.department}
    return render_template("notices_form.html", notice=notice_dict, departments=DEPARTMENTS)

@app.route("/notices/<notice_id>/delete", methods=["POST"])
@role_required("faculty", "club")
def delete_notice(notice_id):
    notice = Notice.query.get(notice_id)
    if notice and notice.author_uid == session["uid"]:
        db.session.delete(notice)
        db.session.commit()
        flash("Notice deleted.", "success")
    else:
        flash("Permission denied.", "danger")
    return redirect(url_for("notices"))

# ===========================================================================
# ASSIGNMENTS
# ===========================================================================

@app.route("/assignments")
@login_required
def assignments():
    dept_filter = request.args.get("department", "")
    query = Assignment.query.order_by(Assignment.created_at.desc())
    if dept_filter:
        query = query.filter_by(department=dept_filter)
        
    docs = query.all()
    items = [{"id": d.id, "title": d.title, "description": d.description, "deadline": d.deadline, "subject": d.subject, "department": d.department, "author_name": d.author_name, "author_uid": d.author_uid, "created_at": d.created_at.isoformat() if d.created_at else ""} for d in docs]
    return render_template("assignments.html", assignments=items, departments=DEPARTMENTS)

@app.route("/assignments/create", methods=["GET", "POST"])
@role_required("faculty")
def create_assignment():
    if request.method == "POST":
        uid = session["uid"]
        user = get_current_user()
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return render_template("assignments_form.html", departments=DEPARTMENTS)
            
        assignment = Assignment(
            title=title,
            description=request.form.get("description", "").strip(),
            deadline=request.form.get("deadline", "").strip(),
            department=request.form.get("department", ""),
            subject=request.form.get("subject", "").strip(),
            author_uid=uid,
            author_name=user.get("name", "Unknown") if user else "Unknown"
        )
        db.session.add(assignment)
        db.session.commit()
        flash("Assignment created.", "success")
        return redirect(url_for("assignments"))
    return render_template("assignments_form.html", departments=DEPARTMENTS)

@app.route("/assignments/<assignment_id>/edit", methods=["GET", "POST"])
@role_required("faculty")
def edit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.author_uid != session["uid"]:
        flash("You can only edit your own assignments.", "danger")
        return redirect(url_for("assignments"))
        
    if request.method == "POST":
        assignment.title = request.form.get("title", "").strip()
        assignment.description = request.form.get("description", "").strip()
        assignment.deadline = request.form.get("deadline", "").strip()
        assignment.department = request.form.get("department", "")
        assignment.subject = request.form.get("subject", "").strip()
        assignment.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash("Assignment updated.", "success")
        return redirect(url_for("assignments"))
        
    assignment_dict = {"id": assignment.id, "title": assignment.title, "description": assignment.description, "deadline": assignment.deadline, "department": assignment.department, "subject": assignment.subject}
    return render_template("assignments_form.html", assignment=assignment_dict, departments=DEPARTMENTS)

@app.route("/assignments/<assignment_id>/delete", methods=["POST"])
@role_required("faculty")
def delete_assignment(assignment_id):
    assignment = Assignment.query.get(assignment_id)
    if assignment and assignment.author_uid == session["uid"]:
        db.session.delete(assignment)
        db.session.commit()
        flash("Assignment deleted.", "success")
    else:
        flash("Permission denied.", "danger")
    return redirect(url_for("assignments"))

# ===========================================================================
# NOTES
# ===========================================================================

@app.route("/notes")
@login_required
def notes():
    dept_filter = request.args.get("department", "")
    query = Note.query.order_by(Note.created_at.desc())
    if dept_filter:
        query = query.filter_by(department=dept_filter)
        
    docs = query.all()
    items = []
    for d in docs:
        file_url = url_for("serve_file", file_id=d.file_id) if d.file_id else ""
        items.append({
            "id": d.id, "title": d.title, "subject": d.subject, "department": d.department,
            "description": d.description, "file_url": file_url, "file_name": d.file_name,
            "file_type": d.file_type, "uploader_name": d.uploader_name, "uploader_role": d.uploader_role,
            "created_at": d.created_at.isoformat() if d.created_at else ""
        })
    return render_template("notes.html", notes=items, departments=DEPARTMENTS)

@app.route("/notes/upload", methods=["GET", "POST"])
@login_required
def upload_note():
    if request.method == "POST":
        uid = session["uid"]
        user = get_current_user()
        title = request.form.get("title", "").strip()
        file = request.files.get("file")

        if not title or not file or not file.filename:
            flash("Title and file are required.", "danger")
            return render_template("notes_form.html", departments=DEPARTMENTS)

        if not allowed_file(file.filename):
            flash("File type not allowed.", "danger")
            return render_template("notes_form.html", departments=DEPARTMENTS)

        file_data = file.read()
        if len(file_data) > MAX_FILE_SIZE_MB * 1024 * 1024:
            flash(f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.", "danger")
            return render_template("notes_form.html", departments=DEPARTMENTS)

        try:
            ext = file.filename.rsplit(".", 1)[1].lower()
            uploaded_file = UploadedFile(
                filename=file.filename,
                content_type=file.content_type,
                data=file_data
            )
            db.session.add(uploaded_file)
            db.session.flush() # Get ID
            
            note = Note(
                title=title,
                subject=request.form.get("subject", "").strip(),
                department=request.form.get("department", ""),
                description=request.form.get("description", "").strip(),
                file_id=uploaded_file.id,
                file_name=file.filename,
                file_type=ext,
                uploader_uid=uid,
                uploader_name=user.get("name", "Unknown") if user else "Unknown",
                uploader_role=session.get("role")
            )
            db.session.add(note)
            db.session.commit()
            
            flash("Note uploaded successfully.", "success")
            return redirect(url_for("notes"))
        except Exception as e:
            app.logger.error(f"Storage upload error: {e}")
            db.session.rollback()
            flash("File upload failed.", "danger")
            return render_template("notes_form.html", departments=DEPARTMENTS)
            
    return render_template("notes_form.html", departments=DEPARTMENTS)

# ===========================================================================
# DOUBTS
# ===========================================================================

@app.route("/doubts")
@login_required
def doubts():
    uid = session["uid"]
    role = session.get("role")
    query = Doubt.query.order_by(Doubt.created_at.desc())
    
    if role == "student":
        query = query.filter_by(asker_uid=uid)
    elif role in ("faculty", "club"):
        query = query.filter_by(target_uid=uid)
        
    docs = query.all()
    items = [{"id": d.id, "question": d.question, "asker_name": d.asker_name, "target_name": d.target_name, "department": d.department, "answer": d.answer, "answered": d.answered, "created_at": d.created_at.isoformat() if d.created_at else ""} for d in docs]
    return render_template("doubts.html", doubts=items)

@app.route("/doubts/ask", methods=["GET", "POST"])
@role_required("student")
def ask_doubt():
    faculty_list = [{"id": f.id, "name": f.name} for f in User.query.filter_by(role="faculty").all()]
    club_list = [{"id": c.id, "name": c.name} for c in User.query.filter_by(role="club").all()]

    if request.method == "POST":
        uid = session["uid"]
        user = get_current_user()
        question = request.form.get("question", "").strip()
        target_uid = request.form.get("target_uid", "").strip()
        
        if not question or not target_uid:
            flash("Question and recipient are required.", "danger")
            return render_template("doubts_form.html", faculty_list=faculty_list, club_list=club_list, departments=DEPARTMENTS)
            
        doubt = Doubt(
            question=question,
            target_uid=target_uid,
            target_name=request.form.get("target_name", "").strip(),
            target_type=request.form.get("target_type", "faculty"),
            asker_uid=uid,
            asker_name=user.get("name", "Unknown") if user else "Unknown",
            department=request.form.get("department", ""),
        )
        db.session.add(doubt)
        db.session.commit()
        flash("Question submitted successfully.", "success")
        return redirect(url_for("doubts"))
        
    return render_template("doubts_form.html", faculty_list=faculty_list, club_list=club_list, departments=DEPARTMENTS)

@app.route("/doubts/<doubt_id>/answer", methods=["POST"])
@role_required("faculty", "club")
def answer_doubt(doubt_id):
    answer = request.form.get("answer", "").strip()
    if not answer:
        flash("Answer cannot be empty.", "danger")
        return redirect(url_for("doubts"))
        
    doubt = Doubt.query.get(doubt_id)
    if doubt and doubt.target_uid == session["uid"]:
        doubt.answer = answer
        doubt.answered = True
        doubt.answered_at = datetime.now(timezone.utc)
        db.session.commit()
        flash("Answer submitted.", "success")
    return redirect(url_for("doubts"))

# ===========================================================================
# QUIZZES
# ===========================================================================

@app.route("/quizzes")
@login_required
def quizzes():
    uid = session["uid"]
    role = session.get("role")
    
    docs = Quiz.query.order_by(Quiz.created_at.desc()).all()
    items = []
    for d in docs:
        if role == "faculty" and d.creator_uid != uid:
            continue
        items.append({
            "id": d.id, "title": d.title, "department": d.department, "creator_name": d.creator_name,
            "created_at": d.created_at.isoformat() if d.created_at else ""
        })
    return render_template("quizzes.html", quizzes=items)

@app.route("/quizzes/create", methods=["GET", "POST"])
@role_required("faculty")
def create_quiz():
    if request.method == "POST":
        uid = session["uid"]
        user = get_current_user()
        title = request.form.get("title", "").strip()
        questions_json = request.form.get("questions_json", "[]")
        
        try:
            questions = json.loads(questions_json)
        except Exception:
            questions = []
            
        if not title or not questions:
            flash("Title and at least one question are required.", "danger")
            return render_template("quiz_form.html", departments=DEPARTMENTS)
            
        quiz = Quiz(
            title=title,
            department=request.form.get("department", ""),
            questions=json.dumps(questions),
            creator_uid=uid,
            creator_name=user.get("name", "Unknown") if user else "Unknown"
        )
        db.session.add(quiz)
        db.session.commit()
        flash("Quiz created.", "success")
        return redirect(url_for("quizzes"))
        
    return render_template("quiz_form.html", departments=DEPARTMENTS)

@app.route("/quizzes/<quiz_id>/attempt", methods=["GET", "POST"])
@role_required("student")
def attempt_quiz(quiz_id):
    quiz_obj = Quiz.query.get_or_404(quiz_id)
    uid = session["uid"]
    
    existing = QuizResult.query.filter_by(quiz_id=quiz_id, student_uid=uid).first()
    if existing:
        flash("You have already attempted this quiz.", "info")
        return redirect(url_for("quiz_result", quiz_id=quiz_id))
        
    quiz_dict = {"id": quiz_obj.id, "title": quiz_obj.title, "questions": json.loads(quiz_obj.questions)}
    
    if request.method == "POST":
        questions = quiz_dict.get("questions", [])
        score = 0
        answers = []
        for i, q in enumerate(questions):
            selected = request.form.get(f"q_{i}", "")
            correct = q.get("correct", "")
            is_correct = selected == correct
            if is_correct:
                score += q.get("marks", 1)
            answers.append({
                "question": q.get("question", ""),
                "selected": selected,
                "correct": correct,
                "is_correct": is_correct,
            })
        total = sum(q.get("marks", 1) for q in questions)
        
        result = QuizResult(
            quiz_id=quiz_id,
            quiz_title=quiz_obj.title,
            student_uid=uid,
            student_name=session.get("name", ""),
            score=score,
            total=total,
            answers=json.dumps(answers)
        )
        db.session.add(result)
        db.session.commit()
        flash(f"Quiz submitted! Your score: {score}/{total}", "success")
        return redirect(url_for("quiz_result", quiz_id=quiz_id))
        
    return render_template("quiz_attempt.html", quiz=quiz_dict)

@app.route("/quizzes/<quiz_id>/result")
@login_required
def quiz_result(quiz_id):
    uid = session["uid"]
    r = QuizResult.query.filter_by(quiz_id=quiz_id, student_uid=uid).first()
    quiz_obj = Quiz.query.get(quiz_id)
    
    result_data = None
    if r:
        result_data = {"id": r.id, "score": r.score, "total": r.total, "answers": json.loads(r.answers)}
    quiz_data = {}
    if quiz_obj:
        quiz_data = {"id": quiz_obj.id, "title": quiz_obj.title}
        
    return render_template("quiz_result.html", result=result_data, quiz=quiz_data)

# ===========================================================================
# CLASSMATES & SHARING
# ===========================================================================

@app.route("/classmates")
@role_required("student")
def classmates():
    uid = session["uid"]
    user = get_current_user()
    peers = []
    
    if user:
        search = request.args.get("search", "").strip().lower()
        dept_filter = request.args.get("department", user.get("department", ""))
        
        query = User.query.filter_by(role="student").filter(User.id != uid)
        if dept_filter:
            query = query.filter_by(department=dept_filter)
            
        for u in query.all():
            if search and search not in u.name.lower() and search not in (u.roll_number or "").lower():
                continue
            peers.append({
                "id": u.id, "name": u.name, "department": u.department, "roll_number": u.roll_number,
                "bio": u.bio, "avatar_url": u.avatar_url
            })
            
    return render_template("classmates.html", classmates=peers, departments=DEPARTMENTS)

@app.route("/classmates/<peer_id>")
@role_required("student")
def classmate_profile(peer_id):
    peer_obj = User.query.get_or_404(peer_id)
    if peer_obj.role != "student":
        abort(404)
    peer = {
        "id": peer_obj.id, "name": peer_obj.name, "department": peer_obj.department,
        "roll_number": peer_obj.roll_number, "bio": peer_obj.bio, "avatar_url": peer_obj.avatar_url
    }
    return render_template("classmate_profile.html", peer=peer)

# ---------------------------------------------------------------------------
# Messaging (Classmates & Sharing)
# ---------------------------------------------------------------------------

def _get_or_create_conversation(uid1, uid2):
    p1, p2 = (uid1, uid2) if uid1 < uid2 else (uid2, uid1)
    conv_id = f"{p1}_{p2}"
    
    conv = Conversation.query.get(conv_id)
    if not conv:
        u1 = User.query.get(p1)
        u2 = User.query.get(p2)
        conv = Conversation(
            id=conv_id,
            participant1=p1,
            participant2=p2,
            participant1_name=u1.name if u1 else "",
            participant2_name=u2.name if u2 else "",
            last_message=""
        )
        db.session.add(conv)
        db.session.commit()
    return conv_id

@app.route("/messages")
@role_required("student")
def messages():
    uid = session["uid"]
    convs = []
    
    docs = Conversation.query.filter((Conversation.participant1 == uid) | (Conversation.participant2 == uid)).order_by(Conversation.last_message_at.desc()).all()
    for d in docs:
        if d.participant1 == uid:
            peer_name = d.participant2_name
            peer_id = d.participant2
        else:
            peer_name = d.participant1_name
            peer_id = d.participant1
            
        convs.append({
            "id": d.id, "peer_name": peer_name, "peer_id": peer_id,
            "last_message": d.last_message, "last_message_at": d.last_message_at.isoformat() if d.last_message_at else ""
        })
        
    return render_template("messages.html", conversations=convs)

@app.route("/messages/<peer_id>", methods=["GET", "POST"])
@role_required("student")
def chat(peer_id):
    uid = session["uid"]
    peer_obj = User.query.get_or_404(peer_id)
    if peer_obj.role != "student":
        abort(404)
        
    peer = {"id": peer_obj.id, "name": peer_obj.name, "avatar_url": peer_obj.avatar_url}
    conv_id = _get_or_create_conversation(uid, peer_id)
    
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        file = request.files.get("file")
        
        msg = Message(
            conversation_id=conv_id,
            sender_uid=uid,
            sender_name=session.get("name", ""),
            content=content
        )
        
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("File type not allowed.", "danger")
                return redirect(url_for("chat", peer_id=peer_id))
            file_data = file.read()
            if len(file_data) > MAX_FILE_SIZE_MB * 1024 * 1024:
                flash(f"File too large. Max {MAX_FILE_SIZE_MB}MB.", "danger")
                return redirect(url_for("chat", peer_id=peer_id))
                
            try:
                ext = file.filename.rsplit(".", 1)[1].lower()
                uploaded_file = UploadedFile(
                    filename=file.filename,
                    content_type=file.content_type,
                    data=file_data
                )
                db.session.add(uploaded_file)
                db.session.flush()
                
                msg.file_id = uploaded_file.id
                msg.file_name = file.filename
                msg.file_type = ext
            except Exception as e:
                app.logger.error(f"Message file upload error: {e}")
                
        if msg.content or msg.file_id:
            db.session.add(msg)
            
            conv = Conversation.query.get(conv_id)
            conv.last_message = msg.content or f"[{msg.file_type.upper()} file]"
            conv.last_message_at = datetime.now(timezone.utc)
            db.session.commit()
            
        return redirect(url_for("chat", peer_id=peer_id))
        
    msg_docs = Message.query.filter_by(conversation_id=conv_id).order_by(Message.created_at).all()
    chat_messages = []
    for m in msg_docs:
        file_url = url_for("serve_file", file_id=m.file_id) if m.file_id else ""
        chat_messages.append({
            "id": m.id, "sender_uid": m.sender_uid, "sender_name": m.sender_name,
            "content": m.content, "file_url": file_url, "file_name": m.file_name,
            "file_type": m.file_type, "created_at": m.created_at.isoformat() if m.created_at else ""
        })
        
    return render_template("chat.html", peer=peer, messages=chat_messages, conv_id=conv_id)

@app.route("/messages/<conv_id>/delete/<msg_id>", methods=["POST"])
@role_required("student")
def delete_message(conv_id, msg_id):
    uid = session["uid"]
    msg = Message.query.get(msg_id)
    if msg and msg.conversation_id == conv_id and msg.sender_uid == uid:
        db.session.delete(msg)
        db.session.commit()
    return jsonify({"ok": True})

# ===========================================================================
# STUDY HUB
# ===========================================================================

@app.route("/study-hub")
@login_required
def study_hub():
    uid = session["uid"]
    sessions_data = []
    docs = StudySession.query.filter_by(user_uid=uid).order_by(StudySession.date.desc()).limit(30).all()
    for d in docs:
        sessions_data.append({
            "id": d.id, "date": d.date, "duration_seconds": d.duration_seconds
        })
    return render_template("study_hub.html", sessions=sessions_data)

@app.route("/api/study/save", methods=["POST"])
@login_required
def save_study_session():
    uid = session["uid"]
    data = request.get_json(silent=True) or {}
    duration_seconds = data.get("duration_seconds", 0)
    date_str = data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    
    session_obj = StudySession.query.filter_by(user_uid=uid, date=date_str).first()
    if session_obj:
        session_obj.duration_seconds += duration_seconds
        session_obj.updated_at = datetime.now(timezone.utc)
    else:
        session_obj = StudySession(
            user_uid=uid,
            date=date_str,
            duration_seconds=duration_seconds
        )
        db.session.add(session_obj)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/study/sessions")
@login_required
def get_study_sessions():
    uid = session["uid"]
    docs = StudySession.query.filter_by(user_uid=uid).order_by(StudySession.date.desc()).limit(30).all()
    return jsonify([{"id": d.id, "date": d.date, "duration_seconds": d.duration_seconds} for d in docs])

# ===========================================================================
# ADMIN DASHBOARD
# ===========================================================================

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated

@app.route("/admin")
@admin_required
def admin_dashboard():
    stats = {
        "total_students": 0, "total_faculty": 0, "total_clubs": 0,
        "total_notes": 0, "total_assignments": 0, "total_notices": 0,
        "students": [], "faculty": [], "clubs": [],
    }
    try:
        s_docs = User.query.filter_by(role="student").all()
        stats["students"] = [{"id": d.id, "name": d.name, "email": d.email, "department": d.department, "roll_number": d.roll_number, "is_active": d.is_active} for d in s_docs]
        stats["total_students"] = len(stats["students"])
        
        f_docs = User.query.filter_by(role="faculty").all()
        stats["faculty"] = [{"id": d.id, "name": d.name, "email": d.email, "is_active": d.is_active} for d in f_docs]
        stats["total_faculty"] = len(stats["faculty"])
        
        c_docs = User.query.filter_by(role="club").all()
        stats["clubs"] = [{"id": d.id, "name": d.name, "email": d.email, "is_active": d.is_active} for d in c_docs]
        stats["total_clubs"] = len(stats["clubs"])
        
        stats["total_notes"] = Note.query.count()
        stats["total_assignments"] = Assignment.query.count()
        stats["total_notices"] = Notice.query.count()
    except Exception as e:
        app.logger.error(f"Admin stats error: {e}")
        
    return render_template("admin/dashboard.html", stats=stats)

@app.route("/admin/user/<uid>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(uid):
    user = User.query.get(uid)
    if user:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f"User {'activated' if user.is_active else 'deactivated'}.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/user/<uid>/delete", methods=["POST"])
@admin_required
def admin_delete_user(uid):
    user = User.query.get(uid)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted.", "success")
    return redirect(url_for("admin_dashboard"))

# ===========================================================================
# API - Real-time updates support
# ===========================================================================

@app.route("/api/messages/<conv_id>/poll")
@role_required("student")
def poll_messages(conv_id):
    uid = session["uid"]
    conv = Conversation.query.get(conv_id)
    if not conv or uid not in (conv.participant1, conv.participant2):
        abort(403)
        
    since = request.args.get("since", "")
    query = Message.query.filter_by(conversation_id=conv_id).order_by(Message.created_at)
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            query = query.filter(Message.created_at > since_dt)
        except ValueError:
            pass
            
    docs = query.all()
    res = []
    for m in docs:
        file_url = url_for("serve_file", file_id=m.file_id) if m.file_id else ""
        res.append({
            "id": m.id, "sender_uid": m.sender_uid, "sender_name": m.sender_name,
            "content": m.content, "file_url": file_url, "file_name": m.file_name,
            "file_type": m.file_type, "created_at": m.created_at.isoformat() if m.created_at else ""
        })
    return jsonify(res)

# ===========================================================================
# ERROR HANDLERS
# ===========================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403

@app.errorhandler(500)
def server_error(e):
    return render_template("errors/500.html"), 500

# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(debug=debug, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
