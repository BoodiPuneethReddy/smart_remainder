"""
audit_colleges.py — Audits the SQLite database for colleges and tests search queries.
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent.parent / "study_reminder.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Table Info
print("--- TABLE INFO: colleges ---")
for col in cursor.execute("PRAGMA table_info(colleges)").fetchall():
    print(col)

print("\n--- TABLE INFO: college_aliases ---")
for col in cursor.execute("PRAGMA table_info(college_aliases)").fetchall():
    print(col)

# 2. Count
college_count = cursor.execute("SELECT COUNT(*) FROM colleges").fetchone()[0]
alias_count = cursor.execute("SELECT COUNT(*) FROM college_aliases").fetchone()[0]
print(f"\nTotal Colleges: {college_count}")
print(f"Total Aliases:  {alias_count}")

# 3. Test Direct SQL Queries
def search_sql(q):
    like_str = f"%{q}%"
    sql = """
    SELECT c.id, c.college_name, c.state, c.district, c.is_active
    FROM colleges c
    LEFT JOIN college_aliases ca ON ca.college_id = c.id
    WHERE c.college_name LIKE ? OR c.state LIKE ? OR c.district LIKE ? OR ca.alias LIKE ?
    LIMIT 10
    """
    rows = cursor.execute(sql, (like_str, like_str, like_str, like_str)).fetchall()
    print(f"\n--- SQL Search for '{q}' (Found {len(rows)} sample rows): ---")
    for row in rows:
        print(row)

search_sql("sri")
search_sql("tirupati")
search_sql("IIT")

conn.close()
