"""
Campus Connect 3.0 — SQLite to PostgreSQL Migration Tool
Migrates all users and data from local SQLite database to a cloud PostgreSQL database
(e.g., Neon Postgres, Supabase, or Vercel Postgres) for permanent storage on Vercel.

Usage:
    python migrate_to_postgres.py "postgresql://user:password@host/dbname?sslmode=require"
Or set DATABASE_URL in your .env and run:
    python migrate_to_postgres.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def migrate():
    # 1. Determine target PostgreSQL URL
    if len(sys.argv) > 1 and sys.argv[1].strip():
        pg_url = sys.argv[1].strip()
    else:
        pg_url = os.environ.get("DATABASE_URL", "").strip()

    if not pg_url:
        print("\n" + "=" * 60)
        print("ERROR: No PostgreSQL connection URL provided!")
        print("=" * 60)
        print("Please provide the connection string in one of two ways:")
        print("  1. As a command line argument:")
        print("     python migrate_to_postgres.py \"postgresql://user:pass@ep-xyz.neon.tech/dbname?sslmode=require\"")
        print("  2. In your .env file:")
        print("     DATABASE_URL=postgresql://user:pass@ep-xyz.neon.tech/dbname?sslmode=require")
        print("=" * 60 + "\n")
        sys.exit(1)

    if pg_url.startswith("postgres://"):
        pg_url = "postgresql+psycopg2://" + pg_url[11:]
    elif pg_url.startswith("postgresql://"):
        pg_url = "postgresql+psycopg2://" + pg_url[13:]

    print("\n" + "=" * 60)
    print("Campus Connect 3.0 — SQLite to PostgreSQL Data Migration")
    print("=" * 60)
    print(f"Target Database: {pg_url.split('@')[-1] if '@' in pg_url else 'PostgreSQL'}")

    from app import app
    from models import (
        db, User, UploadedFile, Notice, Assignment, Note, NoteShare,
        AssignmentSubmission, Doubt, Quiz, QuizResult, Conversation,
        Message, StudySession, Task, ExamReminder, LoginLog, ActivityLog
    )

    # Tables in topological dependency order
    model_classes = [
        User,
        UploadedFile,
        Notice,
        Assignment,
        AssignmentSubmission,
        Note,
        NoteShare,
        Doubt,
        Quiz,
        Conversation,
        StudySession,
        QuizResult,
        Message,
        Task,
        ExamReminder,
        LoginLog,
        ActivityLog
    ]

    # Read from SQLite first
    sqlite_data = {}
    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "campus_connect.db")
    if not os.path.exists(sqlite_path):
        print(f"Warning: Local SQLite database not found at {sqlite_path}. Nothing to migrate.")
        return

    print(f"\n1. Reading existing data from local SQLite ({sqlite_path})...")
    with app.app_context():
        # App is currently connected to sqlite by default
        for model in model_classes:
            try:
                records = model.query.all()
                sqlite_data[model.__name__] = records
                print(f"   - {model.__tablename__}: {len(records)} record(s) found")
            except Exception as e:
                print(f"   - {model.__tablename__}: Error reading ({e})")
                sqlite_data[model.__name__] = []

    # Now re-bind app to PostgreSQL and write
    print("\n2. Connecting to PostgreSQL and creating schema...")
    app.config['SQLALCHEMY_DATABASE_URI'] = pg_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    
    with app.app_context():
        db.engine.dispose()
        db.create_all()
        print("   Schema verified / created successfully!")

        print("\n3. Migrating records into PostgreSQL...")
        for model in model_classes:
            name = model.__name__
            records = sqlite_data.get(name, [])
            if not records:
                continue

            migrated_count = 0
            for item in records:
                # Extract column values into dict
                cols = {c.name: getattr(item, c.name) for c in item.__table__.columns}
                try:
                    # Check if record already exists by primary key
                    pk_val = cols.get('id')
                    existing = None
                    if pk_val:
                        existing = db.session.get(model, pk_val)
                    if not existing:
                        new_item = model(**cols)
                        db.session.add(new_item)
                        migrated_count += 1
                except Exception as ex:
                    print(f"   [!] Skipped record in {name}: {ex}")

            try:
                db.session.commit()
                print(f"   + {model.__tablename__}: {migrated_count} new record(s) inserted.")
            except Exception as e:
                db.session.rollback()
                print(f"   [!] Failed to commit {name}: {e}")

    print("\n" + "=" * 60)
    print("Migration Complete! Your PostgreSQL database is ready for Vercel.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    migrate()
