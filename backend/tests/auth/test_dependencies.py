import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError, AuthRetryableError

from app.main import app

USER_ID = uuid.uuid4()


class FakeAuth:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.received_jwt: str | None = None

    async def get_user(self, jwt: str):
        self.received_jwt = jwt
        if self.error:
            raise self.error
        return self.result


def valid_user_response(email: str | None = "analyst@example.com"):
    return SimpleNamespace(user=SimpleNamespace(id=str(USER_ID), email=email))


@pytest.fixture
def client_with(monkeypatch):
    def build(auth: FakeAuth) -> TestClient:
        # Not used as a context manager, so the lifespan (real Supabase client) never runs.
        monkeypatch.setattr(app.state, "supabase", SimpleNamespace(auth=auth), raising=False)
        return TestClient(app)

    return build


def test_missing_token_returns_401_without_calling_supabase(client_with):
    auth = FakeAuth(result=valid_user_response())
    response = client_with(auth).get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert auth.received_jwt is None


def test_invalid_or_expired_token_returns_401(client_with):
    auth = FakeAuth(error=AuthApiError("invalid JWT", 403, "bad_jwt"))
    response = client_with(auth).get("/auth/me", headers={"Authorization": "Bearer expired"})

    assert response.status_code == 401


def test_user_without_email_returns_401(client_with):
    auth = FakeAuth(result=valid_user_response(email=None))
    response = client_with(auth).get("/auth/me", headers={"Authorization": "Bearer token"})

    assert response.status_code == 401


def test_supabase_outage_returns_502_not_401(client_with):
    auth = FakeAuth(error=AuthRetryableError("upstream down", 503))
    response = client_with(auth).get("/auth/me", headers={"Authorization": "Bearer token"})

    assert response.status_code == 502


def test_valid_token_returns_current_user(client_with):
    auth = FakeAuth(result=valid_user_response())
    response = client_with(auth).get("/auth/me", headers={"Authorization": "Bearer good-token"})

    assert response.status_code == 200
    assert response.json() == {"id": str(USER_ID), "email": "analyst@example.com"}
    assert auth.received_jwt == "good-token"
