import sys
import os
from datetime import datetime, timezone
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../app"))

from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.user import User
from app.models.college import College

def run_account_reset():
    print("================================================================================")
    print("                ACCOUNT RESET PROTOCOL — FULL DATABASE WIPE                    ")
    print("================================================================================")

    db = SessionLocal()

    # Step 1: Wipe all tables in schema
    print("1. Deleting all records from all database tables...")
    table_names = [
        "tutor_message_chunks", "question_citations", "tutor_bookmarks",
        "tutor_messages", "tutor_sessions", "mistake_journal",
        "learning_profiles", "learning_objectives", "imported_documents",
        "recommendations", "notifications", "study_sessions",
        "tasks", "otp_codes", "users"
    ]

    for tbl in table_names:
        try:
            db.execute(text(f"DELETE FROM {tbl};"))
            print(f"   • Wiped table: {tbl}")
        except Exception as e:
            print(f"   • Notice on table {tbl}: {e}")

    db.commit()

    # Step 2: Ensure College 'SVCE' exists or fetch ID
    svce_college = db.query(College).filter(
        (College.college_name.like("%Sri Venkateswara College of Engineering%")) |
        (College.college_name == "SVCE")
    ).first()

    college_id = None
    if svce_college:
        college_id = svce_college.id
        print(f"2. Found College: {svce_college.college_name} (ID: {college_id})")
    else:
        new_col = College(
            college_name="Sri Venkateswara College of Engineering (SVCE)",
            state="Tamil Nadu",
            district="Kanchipuram",
            is_active=True
        )
        db.add(new_col)
        db.commit()
        db.refresh(new_col)
        college_id = new_col.id
        print(f"2. Created College: {new_col.college_name} (ID: {college_id})")

    # Step 3: Create single real user
    email = "punithgodof@gmail.com"
    password = "Punith@123"
    full_name = "Punith"

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        college_id=college_id,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"3. Created Single Real Account: {email} (User ID: {user.id})")

    # Step 4: Verify Counts
    print("\n================================================================================")
    print("                    POST-RESET VERIFICATION SUMMARY                             ")
    print("================================================================================")
    for tbl in table_names:
        res = db.execute(text(f"SELECT COUNT(*) FROM {tbl};")).scalar()
        print(f"   • {tbl:<25}: {res:<4} records")
    
    col_count = db.query(College).count()
    print(f"   • {'colleges':<25}: {col_count:<4} records")

    print("================================================================================")
    print("ACCOUNT RESET COMPLETE — CLEAN SLATE READY.")

if __name__ == "__main__":
    run_account_reset()
