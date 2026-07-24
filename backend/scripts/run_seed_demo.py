import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.seed.seed_data import seed_database

def run_seed():
    db = SessionLocal()
    seed_database(db)
    db.close()
    print("[PASS] Demo account punithgodof@gmail.com seeded cleanly with 8 tasks & study sessions!")

if __name__ == "__main__":
    run_seed()
