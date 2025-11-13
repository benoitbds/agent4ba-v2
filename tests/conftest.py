"""Configuration pytest pour les tests d'authentification."""

import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent4ba.api.main import app
from agent4ba.services.user_service import UserService


@pytest.fixture
def temp_user_storage():
    """
    Crée un fichier temporaire unique pour le stockage des utilisateurs.

    Cette fixture est recréée pour chaque test (scope=function par défaut),
    garantissant l'isolation complète entre les tests.

    Yields:
        Path: Chemin vers le fichier temporaire
    """
    # Créer un nom de fichier unique pour éviter les collisions
    unique_id = str(uuid.uuid4())
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"_{unique_id}.json",
        delete=False,
        prefix="test_users_",
    )
    temp_path = Path(temp_file.name)
    temp_file.write("[]")
    temp_file.close()

    yield temp_path

    # Cleanup : supprimer le fichier après le test
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def client(temp_user_storage, monkeypatch):
    """
    Crée un client de test FastAPI avec un stockage utilisateur temporaire isolé.

    Args:
        temp_user_storage: Fixture fournissant un fichier temporaire unique
        monkeypatch: Fixture pytest pour le monkey patching

    Returns:
        TestClient: Client de test configuré
    """
    # Patcher l'instance singleton UserService dans le module auth
    # pour qu'elle utilise notre stockage temporaire
    from agent4ba.api import auth

    monkeypatch.setattr(auth.user_service, "storage_path", temp_user_storage)

    return TestClient(app)


@pytest.fixture
def registered_user(client):
    """
    Enregistre un utilisateur de test et retourne ses credentials.

    Args:
        client: Client de test FastAPI

    Returns:
        dict: Dictionnaire avec username et password
    """
    # Générer un username unique pour éviter les collisions entre tests
    unique_username = f"testuser_{uuid.uuid4().hex[:8]}"

    response = client.post(
        "/auth/register",
        json={"username": unique_username, "password": "testpass123"},
    )
    assert response.status_code == 201, f"Registration failed: {response.json()}"

    return {"username": unique_username, "password": "testpass123"}


@pytest.fixture
def auth_token(client, registered_user):
    """
    Enregistre un utilisateur et retourne un token d'authentification valide.

    Args:
        client: Client de test FastAPI
        registered_user: Fixture qui crée un utilisateur

    Returns:
        str: Token JWT valide
    """
    response = client.post(
        "/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]
