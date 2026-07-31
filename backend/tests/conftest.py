import urllib.parse

import pytest
import requests
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import create_all_tables, SessionLocal
from app.models.user import User
from app.core.security import hash_password


@pytest.fixture(scope="session", autouse=True)
def local_backend_client():
    """Run the backend app in-process for tests that use requests against localhost."""
    create_all_tables()
    db = SessionLocal()
    try:
        demo_email = "punithgodof@gmail.com"
        user = db.query(User).filter(User.email == demo_email).first()
        if not user:
            user = User(
                email=demo_email,
                full_name="Punith",
                hashed_password=hash_password("Punith@123"),
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

    client = TestClient(app)
    original_request = requests.Session.request

    def patched_request(self, method, url, *args, **kwargs):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme in {"http", "https"} and parsed.hostname in {"localhost", "127.0.0.1"} and parsed.port == 8000:
            path = parsed.path or "/"
            if parsed.query:
                path = f"{path}?{parsed.query}"
            kwargs.setdefault("timeout", 10)
            return client.request(method, path, *args, **kwargs)
        return original_request(self, method, url, *args, **kwargs)

    requests.Session.request = patched_request
    yield client
    requests.Session.request = original_request
