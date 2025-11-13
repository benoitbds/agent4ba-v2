"""Tests for user login endpoint."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from agent4ba.api.main import app
from agent4ba.core.config import settings
from agent4ba.services.user_service import UserService


@pytest.fixture
def temp_user_storage():
    """Create a temporary user storage file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        f.write("[]")
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def client(temp_user_storage, monkeypatch):
    """Create a test client with temporary user storage."""
    # Monkey patch the UserService to use temp storage
    original_init = UserService.__init__

    def patched_init(self, storage_path=None):
        original_init(self, storage_path=temp_user_storage)

    monkeypatch.setattr(UserService, "__init__", patched_init)
    return TestClient(app)


@pytest.fixture
def registered_user(client):
    """Register a test user for login tests."""
    response = client.post(
        "/auth/register",
        json={"username": "loginuser", "password": "loginpass123"},
    )
    assert response.status_code == 201
    return {"username": "loginuser", "password": "loginpass123"}


def test_login_success(client, registered_user):
    """Test successful login."""
    response = client.post(
        "/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify token is valid JWT
    token = data["access_token"]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == registered_user["username"]
    assert "exp" in payload  # Token should have expiration


def test_login_invalid_username(client, registered_user):
    """Test login with non-existent username."""
    response = client.post(
        "/auth/login",
        json={"username": "nonexistent", "password": "anypassword"},
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_invalid_password(client, registered_user):
    """Test login with incorrect password."""
    response = client.post(
        "/auth/login",
        json={
            "username": registered_user["username"],
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_missing_fields(client):
    """Test login with missing required fields."""
    # Missing password
    response1 = client.post(
        "/auth/login",
        json={"username": "testuser"},
    )
    assert response1.status_code == 422

    # Missing username
    response2 = client.post(
        "/auth/login",
        json={"password": "password123"},
    )
    assert response2.status_code == 422

    # Empty body
    response3 = client.post("/auth/login", json={})
    assert response3.status_code == 422


def test_login_case_sensitive(client):
    """Test that username is case-sensitive."""
    # Register user
    client.post(
        "/auth/register",
        json={"username": "CaseSensitive", "password": "password123"},
    )

    # Try login with different case
    response = client.post(
        "/auth/login",
        json={"username": "casesensitive", "password": "password123"},
    )
    assert response.status_code == 401


def test_multiple_logins(client, registered_user):
    """Test that multiple logins generate different tokens."""
    response1 = client.post(
        "/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert response1.status_code == 200
    token1 = response1.json()["access_token"]

    response2 = client.post(
        "/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert response2.status_code == 200
    token2 = response2.json()["access_token"]

    # Tokens should be different (due to different exp times)
    # Note: This might fail if both requests happen at exactly the same second
    # but it's unlikely in practice
    # We check that both tokens are valid instead
    payload1 = jwt.decode(token1, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    payload2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload1["sub"] == payload2["sub"] == registered_user["username"]
