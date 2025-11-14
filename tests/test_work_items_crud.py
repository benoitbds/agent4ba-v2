"""Tests for WorkItem CRUD endpoints."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def temp_project_storage(monkeypatch: pytest.MonkeyPatch):
    """
    Crée un répertoire de stockage temporaire pour les projets.

    Yields:
        Path: Chemin vers le répertoire de stockage temporaire
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        # Patcher le base_path dans ProjectContextService
        from agent4ba.core.storage import ProjectContextService

        original_init = ProjectContextService.__init__

        def patched_init(self, base_path=None):
            original_init(self, base_path=str(temp_path))

        monkeypatch.setattr(ProjectContextService, "__init__", patched_init)

        yield temp_path


@pytest.fixture(scope="function")
def test_project(client: TestClient, auth_token: str, temp_project_storage: Path):
    """
    Crée un projet de test.

    Args:
        client: Client de test FastAPI
        auth_token: Token d'authentification
        temp_project_storage: Fixture fournissant le stockage temporaire

    Returns:
        str: ID du projet créé
    """
    project_id = "test-project"
    response = client.post(
        "/projects",
        json={"project_id": project_id},
    )
    assert response.status_code == 201
    return project_id


def test_create_work_item_success(
    client: TestClient, auth_token: str, test_project: str
):
    """Test creating a new WorkItem successfully."""
    work_item_data = {
        "type": "story",
        "title": "Implement user authentication",
        "description": "As a user, I want to log in...",
        "acceptance_criteria": ["User can login with email and password"],
        "attributes": {
            "priority": "high",
            "status": "todo",
            "points": 8,
        },
    }

    response = client.post(
        f"/projects/{test_project}/work_items",
        json=work_item_data,
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 201
    data = response.json()

    # Vérifier que l'ID a été généré
    assert "id" in data
    assert data["id"].startswith("WI-")

    # Vérifier que le project_id a été assigné
    assert data["project_id"] == test_project

    # Vérifier que le validation_status est human_validated
    assert data["validation_status"] == "human_validated"

    # Vérifier les autres champs
    assert data["type"] == work_item_data["type"]
    assert data["title"] == work_item_data["title"]
    assert data["description"] == work_item_data["description"]
    assert data["acceptance_criteria"] == work_item_data["acceptance_criteria"]
    assert data["attributes"] == work_item_data["attributes"]


def test_create_work_item_without_auth(client: TestClient, test_project: str):
    """Test that creating a WorkItem without authentication fails."""
    work_item_data = {
        "type": "story",
        "title": "Test story",
    }

    response = client.post(
        f"/projects/{test_project}/work_items",
        json=work_item_data,
    )

    assert response.status_code == 401


def test_create_work_item_nonexistent_project(client: TestClient, auth_token: str):
    """Test creating a WorkItem in a non-existent project."""
    work_item_data = {
        "type": "story",
        "title": "Test story",
    }

    response = client.post(
        "/projects/nonexistent-project/work_items",
        json=work_item_data,
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 404


def test_update_work_item_success(
    client: TestClient, auth_token: str, test_project: str
):
    """Test updating an existing WorkItem successfully."""
    # First, create a WorkItem
    create_response = client.post(
        f"/projects/{test_project}/work_items",
        json={"type": "story", "title": "Original title"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["id"]

    # Now update it
    update_data = {
        "title": "Updated title",
        "attributes": {
            "priority": "critical",
            "status": "in_progress",
        },
    }

    response = client.put(
        f"/projects/{test_project}/work_items/{item_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Vérifier que les champs ont été mis à jour
    assert data["title"] == "Updated title"
    assert data["attributes"]["priority"] == "critical"
    assert data["attributes"]["status"] == "in_progress"

    # Vérifier que le validation_status a été maintenu à human_validated
    assert data["validation_status"] == "human_validated"

    # Vérifier que l'ID n'a pas changé
    assert data["id"] == item_id


def test_update_work_item_without_auth(
    client: TestClient, auth_token: str, test_project: str
):
    """Test that updating a WorkItem without authentication fails."""
    # First, create a WorkItem
    create_response = client.post(
        f"/projects/{test_project}/work_items",
        json={"type": "story", "title": "Test story"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["id"]

    # Try to update without auth
    response = client.put(
        f"/projects/{test_project}/work_items/{item_id}",
        json={"title": "Updated title"},
    )

    assert response.status_code == 401


def test_update_nonexistent_work_item(client: TestClient, auth_token: str, test_project: str):
    """Test updating a non-existent WorkItem."""
    response = client.put(
        f"/projects/{test_project}/work_items/WI-999",
        json={"title": "Updated title"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 404


def test_delete_work_item_success(
    client: TestClient, auth_token: str, test_project: str
):
    """Test deleting a WorkItem successfully."""
    # First, create a WorkItem
    create_response = client.post(
        f"/projects/{test_project}/work_items",
        json={"type": "story", "title": "To be deleted"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["id"]

    # Delete it
    response = client.delete(
        f"/projects/{test_project}/work_items/{item_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 204

    # Verify it's gone by checking the backlog
    backlog_response = client.get(
        f"/projects/{test_project}/backlog",
    )
    assert backlog_response.status_code == 200
    backlog = backlog_response.json()

    # The item should not be in the backlog
    assert all(item["id"] != item_id for item in backlog)


def test_delete_work_item_without_auth(
    client: TestClient, auth_token: str, test_project: str
):
    """Test that deleting a WorkItem without authentication fails."""
    # First, create a WorkItem
    create_response = client.post(
        f"/projects/{test_project}/work_items",
        json={"type": "story", "title": "Test story"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["id"]

    # Try to delete without auth
    response = client.delete(
        f"/projects/{test_project}/work_items/{item_id}",
    )

    assert response.status_code == 401


def test_delete_nonexistent_work_item(client: TestClient, auth_token: str, test_project: str):
    """Test deleting a non-existent WorkItem."""
    response = client.delete(
        f"/projects/{test_project}/work_items/WI-999",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 404


def test_crud_workflow(client: TestClient, auth_token: str, test_project: str):
    """
    Test the complete CRUD workflow:
    1. Create a WorkItem
    2. Verify it exists in the backlog
    3. Update it
    4. Verify the update
    5. Delete it
    6. Verify it's gone
    """
    # 1. Create
    create_data = {
        "type": "story",
        "title": "Test CRUD workflow",
        "description": "Testing the full CRUD workflow",
        "acceptance_criteria": ["Create works", "Update works", "Delete works"],
        "attributes": {"priority": "medium"},
    }

    create_response = client.post(
        f"/projects/{test_project}/work_items",
        json=create_data,
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["id"]

    # 2. Verify it exists
    backlog_response = client.get(f"/projects/{test_project}/backlog")
    assert backlog_response.status_code == 200
    backlog = backlog_response.json()
    assert any(item["id"] == item_id for item in backlog)

    # 3. Update
    update_data = {
        "title": "Updated CRUD workflow",
        "attributes": {"priority": "high", "status": "in_progress"},
    }

    update_response = client.put(
        f"/projects/{test_project}/work_items/{item_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert update_response.status_code == 200

    # 4. Verify the update
    backlog_response = client.get(f"/projects/{test_project}/backlog")
    assert backlog_response.status_code == 200
    backlog = backlog_response.json()
    updated_item = next((item for item in backlog if item["id"] == item_id), None)
    assert updated_item is not None
    assert updated_item["title"] == "Updated CRUD workflow"
    assert updated_item["attributes"]["priority"] == "high"
    assert updated_item["attributes"]["status"] == "in_progress"

    # 5. Delete
    delete_response = client.delete(
        f"/projects/{test_project}/work_items/{item_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert delete_response.status_code == 204

    # 6. Verify it's gone
    backlog_response = client.get(f"/projects/{test_project}/backlog")
    assert backlog_response.status_code == 200
    backlog = backlog_response.json()
    assert all(item["id"] != item_id for item in backlog)


def test_sequential_ids(client: TestClient, auth_token: str, test_project: str):
    """Test that WorkItem IDs are generated sequentially."""
    # Create first item
    response1 = client.post(
        f"/projects/{test_project}/work_items",
        json={"type": "story", "title": "First item"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response1.status_code == 201
    id1 = response1.json()["id"]
    assert id1 == "WI-001"

    # Create second item
    response2 = client.post(
        f"/projects/{test_project}/work_items",
        json={"type": "story", "title": "Second item"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response2.status_code == 201
    id2 = response2.json()["id"]
    assert id2 == "WI-002"

    # Create third item
    response3 = client.post(
        f"/projects/{test_project}/work_items",
        json={"type": "story", "title": "Third item"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response3.status_code == 201
    id3 = response3.json()["id"]
    assert id3 == "WI-003"
