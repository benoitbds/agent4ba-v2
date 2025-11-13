"""Tests for user login endpoint."""

import pytest
from jose import jwt  # type: ignore[import-untyped]

from agent4ba.core.config import settings


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


def test_login_invalid_username(client):
    """Test login with non-existent username."""
    response = client.post(
        "/auth/login",
        json={"username": "nonexistent_user_xyz", "password": "anypassword"},
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_invalid_password(client, registered_user):
    """Test login with incorrect password."""
    response = client.post(
        "/auth/login",
        json={
            "username": registered_user["username"],
            "password": "wrongpassword123",
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
    # Register user with specific case
    client.post(
        "/auth/register",
        json={"username": "CaseSensitiveUser", "password": "password123"},
    )

    # Try login with different case
    response = client.post(
        "/auth/login",
        json={"username": "casesensitiveuser", "password": "password123"},
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

    # Both tokens should be valid
    payload1 = jwt.decode(token1, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    payload2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload1["sub"] == payload2["sub"] == registered_user["username"]
