from datetime import datetime, timezone
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Student specific
    department = db.Column(db.String(100))
    roll_number = db.Column(db.String(50))
    year = db.Column(db.String(20))
    
    # Faculty specific
    designation = db.Column(db.String(100))
    # For array of departments we can use a comma separated string in sqlite/postgres or a related table
    # Since it was a list in Firebase, we'll store it as JSON string
    departments = db.Column(db.Text, default='[]')
    
    # Club specific
    club_name = db.Column(db.String(100))
    club_category = db.Column(db.String(100))
    
    # Common profile fields
    bio = db.Column(db.Text)
    description = db.Column(db.Text)
    avatar_url = db.Column(db.String(255))

    # Activity & login tracking
    last_login_at = db.Column(db.DateTime(timezone=True))
    login_count = db.Column(db.Integer, default=0)

class Notice(db.Model):
    __tablename__ = 'notices'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(100))
    author_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    author_name = db.Column(db.String(100))
    author_role = db.Column(db.String(20))
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True))

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.String(100))
    department = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    author_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    author_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True))

class UploadedFile(db.Model):
    __tablename__ = 'uploaded_files'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100))
    data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100))
    department = db.Column(db.String(100))
    description = db.Column(db.Text)
    file_id = db.Column(db.String(36), db.ForeignKey('uploaded_files.id'))
    file_name = db.Column(db.String(255))
    file_type = db.Column(db.String(20))
    uploader_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    uploader_name = db.Column(db.String(100))
    uploader_role = db.Column(db.String(20))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

class Doubt(db.Model):
    __tablename__ = 'doubts'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    question = db.Column(db.Text, nullable=False)
    target_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    target_name = db.Column(db.String(100))
    target_type = db.Column(db.String(20))
    asker_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    asker_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    answer = db.Column(db.Text)
    answered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    answered_at = db.Column(db.DateTime(timezone=True))

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100))
    questions = db.Column(db.Text, nullable=False) # JSON string
    creator_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    creator_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

class QuizResult(db.Model):
    __tablename__ = 'quiz_results'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    quiz_id = db.Column(db.String(36), db.ForeignKey('quizzes.id'))
    quiz_title = db.Column(db.String(200))
    student_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    student_name = db.Column(db.String(100))
    score = db.Column(db.Integer)
    total = db.Column(db.Integer)
    answers = db.Column(db.Text) # JSON string
    submitted_at = db.Column(db.DateTime(timezone=True), default=utcnow)

class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.String(100), primary_key=True) # uid1_uid2
    participant1 = db.Column(db.String(36), db.ForeignKey('users.id'))
    participant2 = db.Column(db.String(36), db.ForeignKey('users.id'))
    participant1_name = db.Column(db.String(100))
    participant2_name = db.Column(db.String(100))
    last_message = db.Column(db.Text)
    last_message_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    conversation_id = db.Column(db.String(100), db.ForeignKey('conversations.id'))
    sender_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    sender_name = db.Column(db.String(100))
    content = db.Column(db.Text)
    file_id = db.Column(db.String(36), db.ForeignKey('uploaded_files.id'))
    file_name = db.Column(db.String(255))
    file_type = db.Column(db.String(20))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

class StudySession(db.Model):
    __tablename__ = 'study_sessions'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    date = db.Column(db.String(20)) # YYYY-MM-DD
    duration_seconds = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100))
    description = db.Column(db.Text)
    due_date = db.Column(db.String(50))
    priority = db.Column(db.String(20), default='Medium') # High, Medium, Low
    est_time = db.Column(db.String(50))
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow)

class ExamReminder(db.Model):
    __tablename__ = 'exam_reminders'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_uid = db.Column(db.String(36), db.ForeignKey('users.id'))
    subject = db.Column(db.String(100), nullable=False)
    exam_date = db.Column(db.String(50), nullable=False) # ISO or YYYY-MM-DD
    exam_time = db.Column(db.String(50)) # HH:MM
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

class LoginLog(db.Model):
    __tablename__ = 'login_logs'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id = db.Column(db.String(36), nullable=True) # User ID if matched, else None
    email = db.Column(db.String(120), nullable=False)
    user_name = db.Column(db.String(100))
    role = db.Column(db.String(20)) # 'student', 'faculty', 'club', 'admin', 'unknown'
    status = db.Column(db.String(20), nullable=False) # 'success', 'failed'
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime(timezone=True), default=utcnow)

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id = db.Column(db.String(36), nullable=True)
    user_name = db.Column(db.String(100))
    user_role = db.Column(db.String(20))
    action = db.Column(db.String(100), nullable=False) # e.g. 'notes_uploaded', 'assignment_created', etc.
    category = db.Column(db.String(50), nullable=False) # 'Notes', 'Assignments', 'Auth', 'Planner', etc.
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime(timezone=True), default=utcnow)

def init_db_and_migrate(app):
    """
    Safely creates all database tables and ensures schema backward-compatibility
    without dropping or corrupting any existing data.
    """
    with app.app_context():
        try:
            db.create_all()
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'users' in inspector.get_table_names():
                existing_cols = [c['name'] for c in inspector.get_columns('users')]
                with db.engine.connect() as conn:
                    if 'last_login_at' not in existing_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP"))
                        conn.commit()
                    if 'login_count' not in existing_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN login_count INTEGER DEFAULT 0"))
                        conn.commit()
        except Exception as e:
            app.logger.warning(f"Database migration check warning: {e}")


