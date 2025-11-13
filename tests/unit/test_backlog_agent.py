"""Tests unitaires pour le module backlog_agent."""

import json
from unittest.mock import Mock, patch

import pytest

from agent4ba.ai import backlog_agent


def test_decompose_objective_success():
    """
    Test du cas nominal de la fonction decompose_objective.

    Vérifie que la fonction décompose correctement un objectif en work items
    lorsque le LLM retourne une réponse valide.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "intent": {
            "args": {
                "objective": "Créer un formulaire de connexion"
            }
        },
        "thread_id": "test-thread-123"
    }

    # Préparer les work items que le LLM devrait retourner
    mock_work_items = [
        {
            "id": "TEST-1",
            "project_id": "TEST",
            "type": "feature",
            "title": "Authentification utilisateur",
            "description": "Implémenter un système d'authentification pour les utilisateurs",
            "parent_id": None,
            "attributes": {}
        },
        {
            "id": "TEST-2",
            "project_id": "TEST",
            "type": "story",
            "title": "Formulaire de connexion",
            "description": "En tant qu'utilisateur, je veux me connecter avec mon email et mot de passe",
            "parent_id": "TEST-1",
            "attributes": {}
        },
        {
            "id": "TEST-3",
            "project_id": "TEST",
            "type": "story",
            "title": "Validation des credentials",
            "description": "En tant que système, je veux valider les credentials de l'utilisateur",
            "parent_id": "TEST-1",
            "attributes": {}
        }
    ]

    # Créer le mock de la réponse LLM
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = json.dumps(mock_work_items)

    # Appliquer les patches
    with patch('agent4ba.ai.backlog_agent.completion', return_value=mock_llm_response) as mock_completion, \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None) as mock_event_queue, \
         patch('agent4ba.ai.backlog_agent.assign_sequential_ids', side_effect=lambda proj_id, existing, items: items):

        # Configurer le mock du storage pour retourner une liste vide
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = []
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.decompose_objective(state)

        # Vérifications
        # 1. Vérifier que l'impact_plan existe et n'est pas None
        assert result is not None
        assert "impact_plan" in result
        assert result["impact_plan"] is not None

        # 2. Vérifier que l'impact_plan contient une liste d'opérations (new_items)
        impact_plan = result["impact_plan"]
        assert "new_items" in impact_plan
        assert isinstance(impact_plan["new_items"], list)

        # 3. Vérifier le nombre d'opérations correspond au mock
        assert len(impact_plan["new_items"]) == 3

        # 4. Vérifier que chaque opération est un WorkItem avec les champs attendus
        for i, item in enumerate(impact_plan["new_items"]):
            assert "id" in item
            assert "type" in item
            assert "title" in item
            assert "description" in item
            assert "project_id" in item

            # Vérifier que le project_id a bien été ajouté
            assert item["project_id"] == "TEST"

            # Vérifier que le validation_status a été ajouté
            assert item["validation_status"] == "pending_validation"

        # 5. Vérifier le status de retour
        assert result["status"] == "awaiting_approval"

        # 6. Vérifier que le LLM a bien été appelé
        mock_completion.assert_called_once()

        # 7. Vérifier le contenu du message d'appel au LLM
        call_args = mock_completion.call_args
        assert call_args is not None
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Créer un formulaire de connexion" in messages[1]["content"]

        # 8. Vérifier que modified_items et deleted_items sont vides
        assert impact_plan["modified_items"] == []
        assert impact_plan["deleted_items"] == []
