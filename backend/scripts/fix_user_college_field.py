import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.models.user import User

def set_college_svce():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "punithgodof@gmail.com").first()
    if user:
        user.college = "SVCE"
        db.commit()
        print(f"[PASS] Updated user {user.email} college field to SVCE!")
    else:
        print("[FAIL] User punithgodof@gmail.com not found!")
    db.close()

if __name__ == "__main__":
    set_college_svce()
