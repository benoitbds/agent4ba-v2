"""Tests unitaires pour le module test_agent."""

import json
from unittest.mock import Mock, patch

import pytest

from agent4ba.ai import test_agent
from agent4ba.core.models import WorkItem


def test_generate_test_cases_success():
    """
    Test du cas nominal de la fonction generate_test_cases.

    Vérifie que la fonction génère correctement des WorkItems de type test_case
    pour une User Story parente lorsque le LLM retourne une réponse valide.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "intent_args": {"work_item_id": "TEST-1"},
        "thread_id": "test-thread-123",
    }

    # Créer un WorkItem de test (User Story parente)
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

    # Préparer les cas de test que le LLM devrait retourner (nouveau format)
    mock_test_cases = [
        {
            "title": "Connexion réussie avec des identifiants valides",
            "scenario": "Given l'utilisateur a un compte actif dans le système\nWhen l'utilisateur saisit des identifiants valides et clique sur 'Se connecter'\nThen l'utilisateur est redirigé vers le tableau de bord",
            "steps": [
                {
                    "step": "Naviguer vers la page de connexion",
                    "expected_result": "La page de connexion s'affiche avec les champs Email et Mot de passe",
                },
                {
                    "step": "Entrer un email valide dans le champ Email",
                    "expected_result": "L'email est affiché dans le champ",
                },
                {
                    "step": "Entrer un mot de passe valide dans le champ Mot de passe",
                    "expected_result": "Le mot de passe est masqué dans le champ",
                },
                {
                    "step": "Cliquer sur le bouton 'Se connecter'",
                    "expected_result": "L'utilisateur est redirigé vers le tableau de bord",
                },
            ],
        },
        {
            "title": "Échec de connexion avec un mot de passe incorrect",
            "scenario": "Given l'utilisateur a un compte actif dans le système\nWhen l'utilisateur saisit un email valide mais un mot de passe incorrect\nThen un message d'erreur s'affiche",
            "steps": [
                {
                    "step": "Naviguer vers la page de connexion",
                    "expected_result": "La page de connexion s'affiche",
                },
                {
                    "step": "Entrer un email valide dans le champ Email",
                    "expected_result": "L'email est affiché dans le champ",
                },
                {
                    "step": "Entrer un mot de passe incorrect dans le champ Mot de passe",
                    "expected_result": "Le mot de passe est masqué dans le champ",
                },
                {
                    "step": "Cliquer sur le bouton 'Se connecter'",
                    "expected_result": "Un message d'erreur 'Email ou mot de passe incorrect' s'affiche",
                },
            ],
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

        # 2. Vérifier que l'impact_plan contient une liste de new_items
        impact_plan = result["impact_plan"]
        assert "new_items" in impact_plan
        assert isinstance(impact_plan["new_items"], list)
        assert len(impact_plan["new_items"]) == 2

        # 3. Vérifier que modified_items est vide
        assert "modified_items" in impact_plan
        assert len(impact_plan["modified_items"]) == 0

        # 4. Vérifier la structure du premier nouveau WorkItem (test_case)
        test_case_item = impact_plan["new_items"][0]
        assert test_case_item["type"] == "test_case"
        assert test_case_item["parent_id"] == "TEST-1"
        assert test_case_item["project_id"] == "TEST"
        assert test_case_item["id"] == "TEST-1-TC001"
        assert test_case_item["title"] == "Connexion réussie avec des identifiants valides"
        assert "scenario" in test_case_item
        assert "Given" in test_case_item["scenario"]
        assert "When" in test_case_item["scenario"]
        assert "Then" in test_case_item["scenario"]

        # 5. Vérifier la structure des steps
        assert "steps" in test_case_item
        assert isinstance(test_case_item["steps"], list)
        assert len(test_case_item["steps"]) == 4
        first_step = test_case_item["steps"][0]
        assert "step" in first_step
        assert "expected_result" in first_step
        assert first_step["step"] == "Naviguer vers la page de connexion"

        # 6. Vérifier le deuxième WorkItem test_case
        second_test_case = impact_plan["new_items"][1]
        assert second_test_case["type"] == "test_case"
        assert second_test_case["parent_id"] == "TEST-1"
        assert second_test_case["id"] == "TEST-1-TC002"
        assert second_test_case["title"] == "Échec de connexion avec un mot de passe incorrect"

        # 7. Vérifier que le statut est "awaiting_approval"
        assert result["status"] == "awaiting_approval"

        # 8. Vérifier que le LLM a été appelé avec les bons paramètres
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
