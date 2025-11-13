"""Tests for user registration endpoint."""

import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_register_success(client):
    """Test successful user registration."""
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpass123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["username"] == "testuser"
    assert "password" not in data  # Password should not be returned
    assert "hashed_password" not in data  # Hashed password should not be returned


def test_register_duplicate_username(client):
    """Test registration with an already existing username."""
    # First registration
    response1 = client.post(
        "/auth/register",
        json={"username": "duplicateuser", "password": "password123"},
    )
    assert response1.status_code == 201

    # Second registration with same username
    response2 = client.post(
        "/auth/register",
        json={"username": "duplicateuser", "password": "differentpass"},
    )
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"].lower()


def test_register_short_username(client):
    """Test registration with username too short."""
    response = client.post(
        "/auth/register",
        json={"username": "ab", "password": "password123"},
    )
    # Should fail validation (minimum 3 characters)
    assert response.status_code == 422


def test_register_short_password(client):
    """Test registration with password too short."""
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "password": "12345"},
    )
    # Should fail validation (minimum 6 characters)
    assert response.status_code == 422


def test_register_missing_fields(client):
    """Test registration with missing required fields."""
    # Missing password
    response1 = client.post(
        "/auth/register",
        json={"username": "testuser"},
    )
    assert response1.status_code == 422

    # Missing username
    response2 = client.post(
        "/auth/register",
        json={"password": "password123"},
    )
    assert response2.status_code == 422

    # Empty body
    response3 = client.post("/auth/register", json={})
    assert response3.status_code == 422


def test_register_password_is_hashed(client, temp_user_storage):
    """Test that password is properly hashed in storage."""
    password = "mysecretpassword"
    response = client.post(
        "/auth/register",
        json={"username": "hashtest", "password": password},
    )
    assert response.status_code == 201

    # Read the storage file directly
    with open(temp_user_storage) as f:
        users = json.load(f)

    # Find the user
    user = next((u for u in users if u["username"] == "hashtest"), None)
    assert user is not None
    assert user["hashed_password"] != password  # Password should be hashed
    assert user["hashed_password"].startswith("$2b$")  # bcrypt hash format
