"""
core/database.py — SQLAlchemy engine, session factory, and declarative Base.
All models import Base from here; all routes import get_db from here.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite requires check_same_thread=False for multi-threaded FastAPI
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.database_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()



def get_db():
    """FastAPI dependency that yields a DB session and ensures it closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    """Create all database tables and add missing columns dynamically."""
    Base.metadata.create_all(bind=engine)

    # Lightweight SQLite column migrations for TutorSession
    with engine.connect() as conn:
        try:
            from sqlalchemy import text
            columns_to_add = [
                ("document_id", "INTEGER"),
                ("difficulty_name", "VARCHAR DEFAULT 'Adaptive'"),
                ("session_length", "VARCHAR DEFAULT '60 min'"),
                ("selected_topics", "TEXT"),
                ("current_concept", "VARCHAR"),
                ("remaining_concepts", "TEXT"),
                ("weak_topics", "TEXT")
            ]
            for col_name, col_type in columns_to_add:
                try:
                    conn.execute(text(f"ALTER TABLE tutor_sessions ADD COLUMN {col_name} {col_type};"))
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            pass
