"""
migrate_db.py — Adds explicit FSM columns to SQLite tutor_sessions table.
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent.parent / "smart_study.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

existing_cols = [info[1] for info in cursor.execute("PRAGMA table_info(tutor_sessions)").fetchall()]

cols_to_add = [
    ("current_state", "TEXT DEFAULT 'WAITING_FOR_ANSWER'"),
    ("current_topic_index", "INTEGER DEFAULT 0"),
    ("current_question_text", "TEXT"),
    ("expected_answer", "TEXT"),
    ("score", "REAL DEFAULT 0.0"),
    ("attempts", "INTEGER DEFAULT 0"),
    ("status", "TEXT DEFAULT 'active'")
]

for col_name, col_def in cols_to_add:
    if col_name not in existing_cols:
        cursor.execute(f"ALTER TABLE tutor_sessions ADD COLUMN {col_name} {col_def}")
        print(f"Added column {col_name} to tutor_sessions table.")

conn.commit()
conn.close()
print("SQLite Migration Complete!")
