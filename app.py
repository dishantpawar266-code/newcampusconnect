import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from functools import wraps
import io

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, abort, send_file
)
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    db, User, Notice, Assignment, UploadedFile, Note, Doubt,
    Quiz, QuizResult, Conversation, Message, StudySession,
    Task, ExamReminder, LoginLog, ActivityLog, init_db_and_migrate
)
from resources_data import RESOURCES_DATA, CATEGORIES, get_recommended_resources, get_spotlight_resource

load_dotenv()

# ---------------------------------------------------------------------------
# App Initialisation
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-prod")

# Secure Private Admin Credentials (accessible only server-side)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@campusconnect.edu").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "AdminSecurePass@2026").strip()

is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    if is_vercel:
        # On Vercel, the app root filesystem is strictly read-only.
        # Use /tmp so serverless functions won't crash if DATABASE_URL is not yet set.
        database_url = "sqlite:////tmp/campus_connect.db"
    else:
        instance_dir = os.path.join(BASE_DIR, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        database_url = f"sqlite:///{os.path.join(instance_dir, 'campus_connect.db')}"
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Serverless pool optimization for PostgreSQL (prevents idle timeouts / dropped connections)
if database_url.startswith("postgresql"):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

db.init_app(app)

# Safely initialize database & ensure table schema backward-compatibility
init_db_and_migrate(app)

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

def format_time_ago(dt):
    if not dt:
        return "recently"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{max(1, seconds)}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    return dt.strftime("%b %d, %Y")

def log_login(user_id=None, user_name=None, email="", role="unknown", status="success"):
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()
        ua = request.headers.get("User-Agent", "")[:250]
        entry = LoginLog(
            user_id=user_id,
            user_name=user_name,
            email=email,
            role=role,
            status=status,
            ip_address=ip or "127.0.0.1",
            user_agent=ua
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        app.logger.warning(f"Error logging login event: {e}")
        db.session.rollback()

def log_activity(user_id=None, user_name=None, user_role=None, action="", category="General", details=""):
    try:
        if not user_name and user_id and user_id != "__admin__":
            u = User.query.get(user_id)
            if u:
                user_name = u.name
                user_role = u.role
        entry = ActivityLog(
            user_id=user_id if user_id != "__admin__" else None,
            user_name=user_name or "System",
            user_role=user_role or "unknown",
            action=action,
            category=category,
            details=details
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        app.logger.warning(f"Error logging activity event: {e}")
        db.session.rollback()

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
        return {"id": "__admin__", "name": "Administrator", "role": "admin", "email": ADMIN_EMAIL}
    
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

        # Log registration event
        log_activity(user_id=user.id, user_name=user.name, user_role=role, action="user_registered", category="Auth", details=f"New {role.capitalize()} registered: {name} ({email})")

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
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        return _handle_login(request.form)
    return render_template("auth/login.html")

def _handle_login(form):
    email = form.get("email", "").strip().lower()
    password = form.get("password", "").strip()

    if not email or not password:
        flash("Email and password are required.", "danger")
        return render_template("auth/login.html")

    # Hidden Admin Authentication via Student Login Entry Point
    if ADMIN_EMAIL and ADMIN_PASSWORD and email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session.clear()
        session["uid"] = "__admin__"
        session["role"] = "admin"
        session["name"] = "Administrator"
        log_login(user_id=None, user_name="Administrator", email=email, role="admin", status="success")
        log_activity(user_id=None, user_name="Administrator", user_role="admin", action="admin_login", category="Auth", details="Administrator authenticated to private Admin Console")
        return redirect(url_for("admin_dashboard"))

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        log_login(user_id=user.id if user else None, user_name=user.name if user else None, email=email, role=user.role if user else "unknown", status="failed")
        flash("Invalid email or password.", "danger")
        return render_template("auth/login.html")
    
    if not user.is_active:
        log_login(user_id=user.id, user_name=user.name, email=email, role=user.role, status="failed")
        flash("Your account has been disabled. Contact admin.", "danger")
        return render_template("auth/login.html")

    # Update activity stats for user
    try:
        user.last_login_at = datetime.now(timezone.utc)
        user.login_count = (user.login_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()

    session["uid"] = user.id
    session["role"] = user.role
    session["name"] = user.name
    log_login(user_id=user.id, user_name=user.name, email=user.email, role=user.role, status="success")
    log_activity(user_id=user.id, user_name=user.name, user_role=user.role, action="user_login", category="Auth", details=f"{user.name} signed in successfully")

    flash(f"Welcome back, {user.name}!", "success")
    return redirect(url_for("dashboard"))

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
    if "uid" in session:
        log_activity(
            user_id=session.get("uid"),
            user_name=session.get("name"),
            user_role=session.get("role"),
            action="file_accessed",
            category="Files",
            details=f"Accessed shared file: {file_record.filename}"
        )
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
    log_activity(session["uid"], session.get("name"), session.get("role"), "planner_task_created", "Planner", f"Created task: '{title}'")
    return jsonify({"ok": True})

@app.route("/api/tasks/<task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    task = Task.query.get(task_id)
    if task and task.user_uid == session["uid"]:
        task.is_completed = not task.is_completed
        task.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        status_txt = "completed" if task.is_completed else "reopened"
        log_activity(session["uid"], session.get("name"), session.get("role"), "planner_task_toggled", "Planner", f"Task '{task.title}' marked as {status_txt}")
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
    log_activity(session["uid"], session.get("name"), session.get("role"), "reminder_created", "Reminders", f"Added exam reminder for '{subject}' ({exam_date})")
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
        log_activity(session["uid"], session.get("name"), session.get("role"), "notice_created", "Notices", f"Published notice: '{title}' ({notice.category})")
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
        log_activity(session["uid"], session.get("name"), session.get("role"), "assignment_created", "Assignments", f"Created assignment: '{title}' ({assignment.subject})")
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
            log_activity(session["uid"], session.get("name"), session.get("role"), "notes_uploaded", "Notes", f"Uploaded note: '{title}' ({note.subject})")
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
        log_activity(session["uid"], session.get("name"), session.get("role"), "doubt_asked", "Doubts", f"Asked doubt to {doubt.target_name}")
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
        log_activity(session["uid"], session.get("name"), session.get("role"), "doubt_answered", "Doubts", f"Answered doubt for {doubt.asker_name}")
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
        log_activity(session["uid"], session.get("name"), session.get("role"), "quiz_created", "Quizzes", f"Created quiz: '{title}' ({quiz.department})")
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
        log_activity(session["uid"], session.get("name"), session.get("role"), "quiz_submitted", "Quizzes", f"Completed quiz: '{quiz_obj.title}' (Score: {score}/{total})")
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
            log_activity(session["uid"], session.get("name"), session.get("role"), "message_sent", "Chat", "Sent a peer chat message" if not msg.file_name else f"Shared file in chat: {msg.file_name}")
            
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
    log_activity(session["uid"], session.get("name"), session.get("role"), "study_timer_saved", "Study Hub", f"Completed {duration_seconds // 60}m study timer session")
    return jsonify({"ok": True})

@app.route("/api/study/sessions")
@login_required
def get_study_sessions():
    uid = session["uid"]
    docs = StudySession.query.filter_by(user_uid=uid).order_by(StudySession.date.desc()).limit(30).all()
    return jsonify([{"id": d.id, "date": d.date, "duration_seconds": d.duration_seconds} for d in docs])

# ===========================================================================
# STUDENT RESOURCE HUB
# ===========================================================================

@app.route("/resources")
@app.route("/resource-hub")
@login_required
def resources():
    log_activity(session.get("uid"), session.get("name"), session.get("role"), "resource_hub_viewed", "Resources Hub", "Explored Student Resource Hub")
    recommended = get_recommended_resources()
    spotlight = get_spotlight_resource()
    return render_template(
        "resources.html",
        resources=RESOURCES_DATA,
        categories=CATEGORIES,
        recommended=recommended,
        spotlight=spotlight
    )

@app.route("/api/track-resource", methods=["POST"])
def track_resource():
    try:
        data = request.get_json(silent=True) or request.form or {}
        r_id = data.get("id", "")
        r_name = data.get("name", "External Resource")
        uid = session.get("uid")
        uname = session.get("name", "Student")
        urole = session.get("role", "student")
        log_activity(
            user_id=uid if uid != "__admin__" else None,
            user_name=uname,
            user_role=urole,
            action="resource_clicked",
            category="Resources Hub",
            details=f"Opened resource: {r_name} ({r_id})"
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ===========================================================================
# ADMIN DASHBOARD
# ===========================================================================

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin" or session.get("uid") != "__admin__":
            if "uid" not in session:
                return redirect(url_for("login"))
            abort(403)
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/logout")
def admin_logout():
    if session.get("role") == "admin":
        log_activity(user_id=None, user_name="Administrator", user_role="admin", action="admin_logout", category="Auth", details="Administrator session terminated")
    session.clear()
    flash("Session signed out successfully.", "info")
    return redirect(url_for("login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. User counts
    total_users = User.query.count()
    students_count = User.query.filter_by(role="student").count()
    faculty_count = User.query.filter_by(role="faculty").count()
    clubs_count = User.query.filter_by(role="club").count()
    active_users_count = User.query.filter_by(is_active=True).count()
    disabled_users_count = User.query.filter_by(is_active=False).count()

    # 2. Registrations
    new_reg_7d = User.query.filter(User.created_at >= seven_days_ago).count()
    new_reg_30d = User.query.filter(User.created_at >= thirty_days_ago).count()

    # 3. Content totals
    total_notes = Note.query.count()
    total_assignments = Assignment.query.count()
    total_notices = Notice.query.count()
    total_quizzes = Quiz.query.count()
    total_quiz_submissions = QuizResult.query.count()
    total_messages = Message.query.count()
    total_files = UploadedFile.query.count()
    total_doubts = Doubt.query.count()
    total_study_sessions = StudySession.query.count()
    total_tasks = Task.query.count()
    total_reminders = ExamReminder.query.count()

    study_seconds = db.session.query(db.func.sum(StudySession.duration_seconds)).scalar() or 0
    total_study_hours = round(study_seconds / 3600.0, 1)

    # 4. Login activity
    total_logins = LoginLog.query.count()
    successful_logins = LoginLog.query.filter_by(status="success").count()
    failed_logins = LoginLog.query.filter_by(status="failed").count()
    success_rate = round((successful_logins / total_logins * 100), 1) if total_logins > 0 else 100.0
    logins_today = LoginLog.query.filter(LoginLog.timestamp >= today_start).count()

    active_users_7d = db.session.query(db.func.count(db.func.distinct(LoginLog.user_id))).filter(
        LoginLog.timestamp >= seven_days_ago,
        LoginLog.user_id.isnot(None),
        LoginLog.status == "success"
    ).scalar() or 0

    active_users_30d = db.session.query(db.func.count(db.func.distinct(LoginLog.user_id))).filter(
        LoginLog.timestamp >= thirty_days_ago,
        LoginLog.user_id.isnot(None),
        LoginLog.status == "success"
    ).scalar() or 0
    if active_users_30d == 0 and active_users_count > 0:
        active_users_30d = active_users_count

    # 5. Most active users (by login_count and activity)
    most_active = User.query.order_by(User.login_count.desc(), User.created_at.desc()).limit(6).all()
    most_active_list = []
    for u in most_active:
        dept_str = u.department or ""
        if u.role == "faculty" and u.departments:
            try:
                d_list = json.loads(u.departments)
                dept_str = ", ".join(d_list) if d_list else "Faculty"
            except Exception:
                dept_str = "Faculty"
        elif u.role == "club":
            dept_str = u.club_category or "Club"

        most_active_list.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "department": dept_str,
            "login_count": u.login_count or 0,
            "last_login": u.last_login_at.strftime("%b %d, %Y %H:%M") if u.last_login_at else "Never",
            "is_active": u.is_active
        })

    # 6. Feature Usage Ranking (Real database counts)
    feature_counts_map = {
        "Notes Hub": total_notes,
        "Assignments": total_assignments,
        "Campus Notices": total_notices,
        "Interactive Quizzes": total_quizzes + total_quiz_submissions,
        "Study Hub & Timer": total_study_sessions,
        "Academic Planner": total_tasks,
        "Exam Reminders": total_reminders,
        "Peer Chat": total_messages,
        "File Sharing": total_files,
        "Doubts & Mentorship": total_doubts,
    }
    # Add activity log category counts
    act_counts = db.session.query(ActivityLog.category, db.func.count(ActivityLog.id)).group_by(ActivityLog.category).all()
    for cat, cnt in act_counts:
        if cat in ("Resources Hub", "Community", "Auth"):
            feature_counts_map[cat] = cnt
        elif cat in feature_counts_map:
            feature_counts_map[cat] = max(feature_counts_map[cat], cnt)

    total_feature_events = sum(feature_counts_map.values()) or 1
    features_ranked = []
    feature_icons = {
        "Notes Hub": "📚", "Assignments": "📋", "Campus Notices": "📢", "Interactive Quizzes": "⚡",
        "Study Hub & Timer": "⏱️", "Academic Planner": "📅", "Exam Reminders": "⏰", "Peer Chat": "💬",
        "File Sharing": "📁", "Doubts & Mentorship": "❓", "Resources Hub": "🌐", "Community": "👥", "Auth": "🔐"
    }
    for name, cnt in sorted(feature_counts_map.items(), key=lambda x: x[1], reverse=True):
        features_ranked.append({
            "name": name,
            "icon": feature_icons.get(name, "✨"),
            "count": cnt,
            "percentage": round((cnt / total_feature_events) * 100, 1)
        })

    most_used_feature = features_ranked[0] if features_ranked else {"name": "None", "count": 0, "percentage": 0, "icon": "⚡"}

    # 7. Complete Users Directory
    users_raw = User.query.order_by(User.created_at.desc()).all()
    user_list = []
    dept_counts = {}
    for u in users_raw:
        dept = u.department or ""
        if u.role == "faculty" and u.departments:
            try:
                depts = json.loads(u.departments)
                dept = ", ".join(depts) if depts else "Faculty"
            except Exception:
                dept = "Faculty"
        elif u.role == "club":
            dept = u.club_category or "Club"
        
        main_dept = u.department or "General"
        dept_counts[main_dept] = dept_counts.get(main_dept, 0) + 1

        user_list.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "department": dept,
            "roll_number": u.roll_number or "—",
            "year": u.year or "—",
            "designation": u.designation or "—",
            "club_name": u.club_name or "—",
            "club_category": u.club_category or "—",
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "—",
            "last_login": u.last_login_at.strftime("%Y-%m-%d %H:%M") if u.last_login_at else "Never",
            "login_count": u.login_count or 0,
            "is_active": u.is_active,
            "bio": u.bio or "",
            "avatar_url": u.avatar_url or ""
        })

    # 8. Recent activity logs (up to 50)
    recent_activities_raw = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(50).all()
    recent_activities = []
    for a in recent_activities_raw:
        recent_activities.append({
            "id": a.id,
            "user_name": a.user_name,
            "user_role": a.user_role,
            "action": a.action,
            "category": a.category,
            "details": a.details,
            "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S") if a.timestamp else "",
            "time_ago": format_time_ago(a.timestamp)
        })

    # If activity log is fresh/empty, build chronological timeline from existing real database records
    if not recent_activities and users_raw:
        for u in users_raw[:10]:
            recent_activities.append({
                "id": u.id,
                "user_name": u.name,
                "user_role": u.role,
                "action": "user_registered",
                "category": "Auth",
                "details": f"Registered as {u.role.capitalize()}",
                "timestamp": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
                "time_ago": format_time_ago(u.created_at)
            })

    # 9. Recent login audit logs (up to 50)
    login_logs_raw = LoginLog.query.order_by(LoginLog.timestamp.desc()).limit(50).all()
    login_logs = []
    for l in login_logs_raw:
        login_logs.append({
            "id": l.id,
            "email": l.email,
            "user_name": l.user_name or "Unknown",
            "role": l.role or "unknown",
            "status": l.status,
            "ip": l.ip_address or "—",
            "ua": l.user_agent or "—",
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S") if l.timestamp else "",
            "time_ago": format_time_ago(l.timestamp)
        })

    # 10. Chart Data
    role_chart = {
        "labels": ["Students", "Faculty", "Clubs"],
        "data": [students_count, faculty_count, clubs_count]
    }
    
    sorted_depts = sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    dept_chart = {
        "labels": [d[0][:24] + ("..." if len(d[0]) > 24 else "") for d in sorted_depts],
        "data": [d[1] for d in sorted_depts]
    }

    days_labels = []
    activity_trend_data = []
    login_success_data = []
    login_failed_data = []
    registrations_trend_data = []
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        days_labels.append(day_date.strftime("%b %d"))
        
        d_start = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0, tzinfo=timezone.utc)
        d_end = datetime(day_date.year, day_date.month, day_date.day, 23, 59, 59, tzinfo=timezone.utc)
        
        acts_count = ActivityLog.query.filter(ActivityLog.timestamp >= d_start, ActivityLog.timestamp <= d_end).count()
        activity_trend_data.append(acts_count)
        
        succ_count = LoginLog.query.filter(LoginLog.timestamp >= d_start, LoginLog.timestamp <= d_end, LoginLog.status == "success").count()
        fail_count = LoginLog.query.filter(LoginLog.timestamp >= d_start, LoginLog.timestamp <= d_end, LoginLog.status == "failed").count()
        login_success_data.append(succ_count)
        login_failed_data.append(fail_count)

        reg_count = User.query.filter(User.created_at >= d_start, User.created_at <= d_end).count()
        registrations_trend_data.append(reg_count)

    feature_chart = {
        "labels": [f["name"] for f in features_ranked[:8]],
        "data": [f["count"] for f in features_ranked[:8]]
    }

    stats = {
        "total_users": total_users,
        "students_count": students_count,
        "faculty_count": faculty_count,
        "clubs_count": clubs_count,
        "active_users_count": active_users_count,
        "disabled_users_count": disabled_users_count,
        "new_reg_7d": new_reg_7d,
        "new_reg_30d": new_reg_30d,
        "total_notes": total_notes,
        "total_assignments": total_assignments,
        "total_notices": total_notices,
        "total_quizzes": total_quizzes,
        "total_quiz_submissions": total_quiz_submissions,
        "total_messages": total_messages,
        "total_files": total_files,
        "total_doubts": total_doubts,
        "total_study_sessions": total_study_sessions,
        "total_study_hours": total_study_hours,
        "total_tasks": total_tasks,
        "total_reminders": total_reminders,
        "total_logins": total_logins,
        "successful_logins": successful_logins,
        "failed_logins": failed_logins,
        "success_rate": success_rate,
        "logins_today": logins_today,
        "active_users_7d": active_users_7d,
        "active_users_30d": active_users_30d,
        "most_used_feature": most_used_feature,
        "features_ranked": features_ranked,
        "most_active_users": most_active_list,
        "users": user_list,
        "recent_activities": recent_activities,
        "login_logs": login_logs,
        "charts": {
            "roles": role_chart,
            "depts": dept_chart,
            "features": feature_chart,
            "days_labels": days_labels,
            "activity_trend": activity_trend_data,
            "login_success": login_success_data,
            "login_failed": login_failed_data,
            "registrations_trend": registrations_trend_data
        }
    }

    return render_template("admin/dashboard.html", stats=stats, departments=DEPARTMENTS)

@app.route("/admin/user/<uid>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(uid):
    user = User.query.get(uid)
    if user:
        user.is_active = not user.is_active
        db.session.commit()
        log_activity(
            user_id=None,
            user_name="Administrator",
            user_role="admin",
            action="user_status_toggled",
            category="User Management",
            details=f"Account for {user.name} ({user.email}) changed to {'Active' if user.is_active else 'Disabled'}"
        )
        flash(f"Account for {user.name} is now {'Activated' if user.is_active else 'Disabled'}.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/user/<uid>/delete", methods=["POST"])
@admin_required
def admin_delete_user(uid):
    user = User.query.get(uid)
    if user:
        name = user.name
        role = user.role
        email = user.email
        db.session.delete(user)
        db.session.commit()
        log_activity(
            user_id=None,
            user_name="Administrator",
            user_role="admin",
            action="user_deleted",
            category="User Management",
            details=f"Permanently deleted {role} account: {name} ({email})"
        )
        flash(f"Account for {name} has been permanently deleted.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/api/user/<uid>")
@admin_required
def admin_api_user_details(uid):
    user = User.query.get(uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    activities = ActivityLog.query.filter_by(user_id=uid).order_by(ActivityLog.timestamp.desc()).limit(15).all()
    user_acts = [{
        "action": a.action,
        "category": a.category,
        "details": a.details,
        "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S") if a.timestamp else "",
        "time_ago": format_time_ago(a.timestamp)
    } for a in activities]

    logins = LoginLog.query.filter_by(user_id=uid).order_by(LoginLog.timestamp.desc()).limit(10).all()
    user_logins = [{
        "status": l.status,
        "ip": l.ip_address,
        "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S") if l.timestamp else "",
        "time_ago": format_time_ago(l.timestamp)
    } for l in logins]

    dept = user.department or ""
    if user.role == "faculty" and user.departments:
        try:
            depts = json.loads(user.departments)
            dept = ", ".join(depts) if depts else "Faculty"
        except Exception:
            dept = "Faculty"
    elif user.role == "club":
        dept = user.club_category or "Club"

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "department": dept,
        "roll_number": user.roll_number or "—",
        "year": user.year or "—",
        "designation": user.designation or "—",
        "club_name": user.club_name or "—",
        "club_category": user.club_category or "—",
        "bio": user.bio or "",
        "is_active": user.is_active,
        "created_at": user.created_at.strftime("%b %d, %Y %H:%M") if user.created_at else "—",
        "last_login": user.last_login_at.strftime("%b %d, %Y %H:%M") if user.last_login_at else "Never",
        "login_count": user.login_count or 0,
        "activities": user_acts,
        "logins": user_logins
    })

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
