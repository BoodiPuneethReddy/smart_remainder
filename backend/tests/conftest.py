import urllib.parse

import pytest
import requests
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session", autouse=True)
def local_backend_client():
    """Run the backend app in-process for tests that use requests against localhost."""
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
