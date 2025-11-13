"""Configuration et fixtures pytest pour tous les tests d'Agent4BA."""

import json
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from agent4ba.api.main import app
from agent4ba.services.user_service import UserService


@pytest.fixture(scope="function")
def temp_user_storage() -> Generator[Path, None, None]:
    """
    Crée un fichier de stockage temporaire pour les utilisateurs.

    Cette fixture est recréée pour chaque test (scope=function) afin d'assurer
    l'isolation complète entre les tests.

    Yields:
        Path: Chemin vers le fichier de stockage temporaire
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        f.write("[]")

    yield temp_path

    # Cleanup après le test
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture(scope="function")
def client(temp_user_storage: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """
    Crée un client de test FastAPI avec un stockage utilisateur temporaire.

    Cette fixture utilise monkeypatch pour remplacer l'instance user_service
    dans le module auth afin qu'elle utilise le fichier de stockage temporaire
    au lieu du fichier par défaut.

    Args:
        temp_user_storage: Fixture fournissant le chemin du stockage temporaire
        monkeypatch: Fixture pytest pour le monkey patching

    Returns:
        TestClient: Client de test configuré
    """
    # Créer une nouvelle instance de UserService avec le stockage temporaire
    from agent4ba.api import auth

    test_user_service = UserService(storage_path=temp_user_storage)

    # Remplacer l'instance globale user_service dans le module auth
    monkeypatch.setattr(auth, "user_service", test_user_service)

    return TestClient(app)


@pytest.fixture(scope="function")
def registered_user(client: TestClient) -> dict[str, str]:
    """
    Enregistre un utilisateur de test et retourne ses credentials.

    Cette fixture est utile pour les tests qui nécessitent un utilisateur déjà enregistré,
    comme les tests de login ou d'authentification.

    Args:
        client: Client de test FastAPI

    Returns:
        dict: Dictionnaire contenant username et password de l'utilisateur créé

    Raises:
        AssertionError: Si l'enregistrement échoue
    """
    credentials = {"username": "testuser", "password": "testpass123"}
    response = client.post("/auth/register", json=credentials)
    assert response.status_code == 201, f"Registration failed: {response.text}"
    return credentials


@pytest.fixture(scope="function")
def auth_token(client: TestClient, registered_user: dict[str, str]) -> str:
    """
    Enregistre un utilisateur et retourne un token d'authentification valide.

    Cette fixture est utile pour tester les endpoints protégés qui nécessitent
    une authentification.

    Args:
        client: Client de test FastAPI
        registered_user: Fixture fournissant un utilisateur enregistré

    Returns:
        str: Token JWT d'authentification

    Raises:
        AssertionError: Si le login échoue
    """
    response = client.post("/auth/login", json=registered_user)
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]  # type: ignore[no-any-return]


# Fixtures pour les tests non-auth (graph, registry, etc.)
# Ces fixtures peuvent être étendues selon les besoins

@pytest.fixture(scope="function")
def test_case() -> dict[str, str]:
    """
    Fixture générique pour les cas de test.

    Peut être utilisée par différents modules de test pour fournir
    des données de test standardisées.

    Returns:
        dict: Dictionnaire de données de test
    """
    return {
        "name": "test_case",
        "query": "Test query",
        "expected_intent": "test_intent",
    }


@pytest.fixture(scope="module")
def graph() -> object:
    """
    Fixture pour le module graph de l'application.

    Scope module car le graph n'a pas besoin d'être rechargé pour chaque test,
    il peut être partagé entre les tests d'un même module.

    Returns:
        object: Module graph importé
    """
    from agent4ba.ai import graph
    return graph


@pytest.fixture(scope="module")
def registry() -> object:
    """
    Fixture pour le service de registre des agents.

    Scope module car le registre peut être partagé entre les tests.

    Returns:
        object: Registry service chargé
    """
    from agent4ba.core.registry_service import load_agent_registry
    return load_agent_registry()
