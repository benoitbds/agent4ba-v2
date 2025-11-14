"""Tests unitaires pour le module test_agent."""

import json
from unittest.mock import Mock, patch

import pytest

from agent4ba.ai import test_agent
from agent4ba.core.models import WorkItem


def test_generate_test_cases_success():
    """
    Test du cas nominal de la fonction generate_test_cases.

    Vérifie que la fonction génère correctement les cas de test pour un work item
    lorsque le LLM retourne une réponse valide.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "intent_args": {"work_item_id": "TEST-1"},
        "thread_id": "test-thread-123",
    }

    # Créer un WorkItem de test
    test_work_item = WorkItem(
        id="TEST-1",
        project_id="TEST",
        type="story",
        title="Page de connexion utilisateur",
        description="En tant qu'utilisateur, je veux pouvoir me connecter avec mon email et mot de passe",
        acceptance_criteria=[
            "L'utilisateur peut saisir son email et son mot de passe",
            "En cas de succès, l'utilisateur est redirigé vers le tableau de bord",
            "Un message d'erreur s'affiche si les identifiants sont incorrects",
        ],
    )

    # Préparer les cas de test que le LLM devrait retourner
    mock_test_cases = [
        {
            "title": "Connexion réussie avec des identifiants valides",
            "description": "Vérifier que l'utilisateur peut se connecter avec des identifiants corrects",
            "preconditions": "L'utilisateur doit avoir un compte actif",
            "steps": [
                "Naviguer vers la page de connexion",
                "Entrer un email valide",
                "Entrer un mot de passe valide",
                "Cliquer sur le bouton 'Se connecter'",
            ],
            "expected_result": "L'utilisateur est redirigé vers le tableau de bord",
        },
        {
            "title": "Échec de connexion avec un mot de passe incorrect",
            "description": "Vérifier que le système refuse la connexion avec un mot de passe incorrect",
            "preconditions": "L'utilisateur doit avoir un compte actif",
            "steps": [
                "Naviguer vers la page de connexion",
                "Entrer un email valide",
                "Entrer un mot de passe incorrect",
                "Cliquer sur le bouton 'Se connecter'",
            ],
            "expected_result": "Un message d'erreur s'affiche",
        },
    ]

    # Créer le mock de la réponse LLM
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = json.dumps(mock_test_cases)

    # Appliquer les patches
    with (
        patch("agent4ba.ai.test_agent.completion", return_value=mock_llm_response) as mock_completion,
        patch("agent4ba.ai.test_agent.ProjectContextService") as mock_storage_class,
        patch("agent4ba.ai.test_agent.get_event_queue", return_value=None) as mock_event_queue,
    ):
        # Configurer le mock du storage pour retourner le work item de test
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = [test_work_item]
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = test_agent.generate_test_cases(state)

        # Vérifications
        # 1. Vérifier que l'impact_plan existe et n'est pas None
        assert result is not None
        assert "impact_plan" in result
        assert result["impact_plan"] is not None

        # 2. Vérifier que l'impact_plan contient une liste de modified_items
        impact_plan = result["impact_plan"]
        assert "modified_items" in impact_plan
        assert isinstance(impact_plan["modified_items"], list)
        assert len(impact_plan["modified_items"]) == 1

        # 3. Vérifier la structure du modified_item
        modified_item = impact_plan["modified_items"][0]
        assert "before" in modified_item
        assert "after" in modified_item

        # 4. Vérifier que l'item "after" contient les cas de test
        item_after = modified_item["after"]
        assert "test_cases" in item_after
        assert isinstance(item_after["test_cases"], list)
        assert len(item_after["test_cases"]) == 2

        # 5. Vérifier la structure d'un cas de test
        test_case = item_after["test_cases"][0]
        assert "title" in test_case
        assert "description" in test_case
        assert "steps" in test_case
        assert "expected_result" in test_case
        assert test_case["title"] == "Connexion réussie avec des identifiants valides"

        # 6. Vérifier que le statut est "awaiting_approval"
        assert result["status"] == "awaiting_approval"

        # 7. Vérifier que le LLM a été appelé avec les bons paramètres
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args
        assert call_args is not None
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


def test_generate_test_cases_item_not_found():
    """
    Test du cas où le work item n'est pas trouvé dans le backlog.

    Vérifie que la fonction retourne une erreur appropriée.
    """
    # Préparer le state initial avec un item_id qui n'existe pas
    state = {
        "project_id": "TEST",
        "intent_args": {"work_item_id": "TEST-999"},
        "thread_id": "test-thread-123",
    }

    # Créer un WorkItem différent
    test_work_item = WorkItem(
        id="TEST-1",
        project_id="TEST",
        type="story",
        title="Autre story",
        description="Description",
    )

    # Appliquer les patches
    with (
        patch("agent4ba.ai.test_agent.ProjectContextService") as mock_storage_class,
        patch("agent4ba.ai.test_agent.get_event_queue", return_value=None) as mock_event_queue,
    ):
        # Configurer le mock du storage
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = [test_work_item]
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = test_agent.generate_test_cases(state)

        # Vérifications
        assert result is not None
        assert result["status"] == "error"
        assert "not found" in result["result"].lower()


def test_generate_test_cases_invalid_json():
    """
    Test du cas où le LLM retourne un JSON invalide.

    Vérifie que la fonction gère correctement les erreurs de parsing JSON.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "intent_args": {"work_item_id": "TEST-1"},
        "thread_id": "test-thread-123",
    }

    # Créer un WorkItem de test
    test_work_item = WorkItem(
        id="TEST-1",
        project_id="TEST",
        type="story",
        title="Test story",
        description="Description",
        acceptance_criteria=["Critère 1"],
    )

    # Créer le mock de la réponse LLM avec un JSON invalide
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = "Invalid JSON {{{{"

    # Appliquer les patches
    with (
        patch("agent4ba.ai.test_agent.completion", return_value=mock_llm_response) as mock_completion,
        patch("agent4ba.ai.test_agent.ProjectContextService") as mock_storage_class,
        patch("agent4ba.ai.test_agent.get_event_queue", return_value=None) as mock_event_queue,
    ):
        # Configurer le mock du storage
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = [test_work_item]
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = test_agent.generate_test_cases(state)

        # Vérifications
        assert result is not None
        assert result["status"] == "error"
        assert "json" in result["result"].lower()


def test_generate_test_cases_no_item_id():
    """
    Test du cas où aucun item_id n'est fourni dans le state.

    Vérifie que la fonction retourne une erreur appropriée.
    """
    # Préparer le state sans item_id
    state = {
        "project_id": "TEST",
        "intent_args": {},
        "thread_id": "test-thread-123",
    }

    # Appliquer les patches
    with patch("agent4ba.ai.test_agent.get_event_queue", return_value=None):
        # Appeler la fonction
        result = test_agent.generate_test_cases(state)

        # Vérifications
        assert result is not None
        assert result["status"] == "error"
        assert "item_id" in result["result"].lower()


def test_generate_test_cases_backlog_not_found():
    """
    Test du cas où le backlog du projet n'existe pas.

    Vérifie que la fonction retourne une erreur appropriée.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "intent_args": {"work_item_id": "TEST-1"},
        "thread_id": "test-thread-123",
    }

    # Appliquer les patches
    with (
        patch("agent4ba.ai.test_agent.ProjectContextService") as mock_storage_class,
        patch("agent4ba.ai.test_agent.get_event_queue", return_value=None) as mock_event_queue,
    ):
        # Configurer le mock du storage pour lever une FileNotFoundError
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.side_effect = FileNotFoundError("Backlog not found")
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = test_agent.generate_test_cases(state)

        # Vérifications
        assert result is not None
        assert result["status"] == "error"
        assert "backlog" in result["result"].lower() or "not found" in result["result"].lower()
