"""Tests unitaires pour les nœuds du graphe LangGraph."""

import json
from unittest.mock import Mock, patch

import pytest

from agent4ba.ai import graph
from agent4ba.core.models import WorkItem


def test_task_rewriter_node_success():
    """
    Test du cas nominal de task_rewriter_node.

    Vérifie que le nœud reformule correctement la requête utilisateur
    en appelant le LLM et retourne la tâche reformulée.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "user_query": "Décompose mon objectif de connexion",
        "context": [
            {
                "type": "work_item",
                "id": "TEST-1",
                "name": "Authentification"
            }
        ]
    }

    # Préparer la réponse du LLM
    mock_rewritten_task = "Générer les user stories pour implémenter un système de connexion utilisateur"

    # Créer le mock de la réponse LLM
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = mock_rewritten_task

    # Mock de la configuration du prompt
    mock_prompt_config = {
        "system_prompt": "You are a task rewriter.",
        "user_prompt_template": "Context: {{ context_summary }}\n\nQuery: {{ user_query }}"
    }

    # Appliquer les patches
    with patch('agent4ba.ai.graph.completion', return_value=mock_llm_response) as mock_completion, \
         patch('agent4ba.ai.graph.load_task_rewriter_prompt', return_value=mock_prompt_config):

        # Appeler la fonction
        result = graph.task_rewriter_node(state)

        # Vérifications
        # 1. Vérifier que le résultat contient rewritten_task
        assert result is not None
        assert "rewritten_task" in result

        # 2. Vérifier que la tâche reformulée correspond au mock
        assert result["rewritten_task"] == mock_rewritten_task

        # 3. Vérifier que completion a été appelé
        assert mock_completion.called
        assert mock_completion.call_count == 1

        # 4. Vérifier que le prompt système a été utilisé
        call_args = mock_completion.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a task rewriter."
        assert messages[1]["role"] == "user"


def test_task_rewriter_node_with_llm_error():
    """
    Test du cas d'erreur de task_rewriter_node.

    Vérifie que le nœud gère correctement une erreur du LLM
    en utilisant la requête originale comme fallback.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "user_query": "Ma requête originale",
        "context": []
    }

    # Mock de la configuration du prompt
    mock_prompt_config = {
        "system_prompt": "You are a task rewriter.",
        "user_prompt_template": "Context: {{ context_summary }}\n\nQuery: {{ user_query }}"
    }

    # Appliquer les patches pour simuler une erreur
    with patch('agent4ba.ai.graph.completion', side_effect=Exception("LLM Error")), \
         patch('agent4ba.ai.graph.load_task_rewriter_prompt', return_value=mock_prompt_config):

        # Appeler la fonction
        result = graph.task_rewriter_node(state)

        # Vérifications
        # 1. Vérifier que le résultat contient rewritten_task
        assert result is not None
        assert "rewritten_task" in result

        # 2. Vérifier que la tâche reformulée est la requête originale (fallback)
        assert result["rewritten_task"] == "Ma requête originale"


def test_approval_node_approved():
    """
    Test du cas où l'utilisateur approuve l'ImpactPlan.

    Vérifie que le nœud applique correctement l'ImpactPlan
    en sauvegardant le backlog avec les nouveaux work items.
    """
    # Préparer l'ImpactPlan
    impact_plan = {
        "new_items": [
            {
                "id": "TEST-10",
                "project_id": "TEST",
                "type": "story",
                "title": "Nouvelle user story",
                "description": "Description de la nouvelle story",
                "parent_id": None,
                "attributes": {}
            },
            {
                "id": "TEST-11",
                "project_id": "TEST",
                "type": "task",
                "title": "Nouvelle tâche",
                "description": "Description de la nouvelle tâche",
                "parent_id": "TEST-10",
                "attributes": {}
            }
        ],
        "modified_items": [],
        "deleted_items": []
    }

    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "approval_decision": True,
        "impact_plan": impact_plan
    }

    # Créer les mocks
    mock_storage_instance = Mock()
    mock_storage_instance.load_context.return_value = []
    mock_storage_instance._find_latest_backlog_version.return_value = 1

    # Appliquer les patches
    with patch('agent4ba.ai.graph.ProjectContextService', return_value=mock_storage_instance) as mock_storage_class:

        # Appeler la fonction
        result = graph.approval_node(state)

        # Vérifications
        # 1. Vérifier que le résultat contient le statut "approved"
        assert result is not None
        assert "status" in result
        assert result["status"] == "approved"

        # 2. Vérifier que le résultat contient un message de succès
        assert "result" in result
        assert "approved and applied successfully" in result["result"]
        assert "Added 2 new work items" in result["result"]

        # 3. Vérifier que load_context a été appelé pour charger le backlog existant
        assert mock_storage_instance.load_context.called
        assert mock_storage_instance.load_context.call_count == 1

        # 4. Vérifier que save_backlog a été appelé avec les bons arguments
        assert mock_storage_instance.save_backlog.called
        assert mock_storage_instance.save_backlog.call_count == 1

        # Récupérer les arguments de l'appel à save_backlog
        call_args = mock_storage_instance.save_backlog.call_args
        saved_project_id = call_args.args[0]
        saved_backlog = call_args.args[1]

        # 5. Vérifier que le project_id est correct
        assert saved_project_id == "TEST"

        # 6. Vérifier que le backlog sauvegardé contient 2 items
        assert len(saved_backlog) == 2

        # 7. Vérifier que les items sont des WorkItem
        for item in saved_backlog:
            assert isinstance(item, WorkItem)


def test_approval_node_rejected():
    """
    Test du cas où l'utilisateur rejette l'ImpactPlan.

    Vérifie que le nœud n'applique pas l'ImpactPlan
    et retourne un message indiquant le rejet.
    """
    # Préparer l'ImpactPlan
    impact_plan = {
        "new_items": [
            {
                "id": "TEST-10",
                "project_id": "TEST",
                "type": "story",
                "title": "Nouvelle user story",
                "description": "Description de la nouvelle story",
                "parent_id": None,
                "attributes": {}
            }
        ],
        "modified_items": [],
        "deleted_items": []
    }

    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "approval_decision": False,
        "impact_plan": impact_plan
    }

    # Créer les mocks
    mock_storage_instance = Mock()

    # Appliquer les patches
    with patch('agent4ba.ai.graph.ProjectContextService', return_value=mock_storage_instance) as mock_storage_class:

        # Appeler la fonction
        result = graph.approval_node(state)

        # Vérifications
        # 1. Vérifier que le résultat contient le statut "rejected"
        assert result is not None
        assert "status" in result
        assert result["status"] == "rejected"

        # 2. Vérifier que le résultat contient un message de rejet
        assert "result" in result
        assert "rejected" in result["result"]
        assert "No changes were applied" in result["result"]

        # 3. Vérifier que load_context n'a JAMAIS été appelé
        assert not mock_storage_instance.load_context.called

        # 4. Vérifier que save_backlog n'a JAMAIS été appelé
        assert not mock_storage_instance.save_backlog.called


def test_approval_node_with_modified_items():
    """
    Test du cas où l'ImpactPlan contient des items modifiés.

    Vérifie que le nœud applique correctement les modifications
    en remplaçant les items existants.
    """
    # Préparer le backlog existant
    existing_items = [
        WorkItem(
            id="TEST-1",
            project_id="TEST",
            type="story",
            title="Ancienne story",
            description="Ancienne description",
            parent_id=None,
            attributes={}
        ),
        WorkItem(
            id="TEST-2",
            project_id="TEST",
            type="task",
            title="Ancienne tâche",
            description="Ancienne description",
            parent_id="TEST-1",
            attributes={}
        )
    ]

    # Préparer l'ImpactPlan avec des items modifiés
    impact_plan = {
        "new_items": [],
        "modified_items": [
            {
                "before": {
                    "id": "TEST-1",
                    "project_id": "TEST",
                    "type": "story",
                    "title": "Ancienne story",
                    "description": "Ancienne description",
                    "parent_id": None,
                    "attributes": {}
                },
                "after": {
                    "id": "TEST-1",
                    "project_id": "TEST",
                    "type": "story",
                    "title": "Story modifiée",
                    "description": "Nouvelle description améliorée",
                    "parent_id": None,
                    "attributes": {}
                }
            }
        ],
        "deleted_items": []
    }

    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "approval_decision": True,
        "impact_plan": impact_plan
    }

    # Créer les mocks
    mock_storage_instance = Mock()
    mock_storage_instance.load_context.return_value = existing_items
    mock_storage_instance._find_latest_backlog_version.return_value = 2

    # Appliquer les patches
    with patch('agent4ba.ai.graph.ProjectContextService', return_value=mock_storage_instance):

        # Appeler la fonction
        result = graph.approval_node(state)

        # Vérifications
        # 1. Vérifier que le résultat contient le statut "approved"
        assert result is not None
        assert "status" in result
        assert result["status"] == "approved"

        # 2. Vérifier que le message indique les modifications
        assert "result" in result
        assert "Modified 1 work items" in result["result"]

        # 3. Vérifier que save_backlog a été appelé
        assert mock_storage_instance.save_backlog.called

        # Récupérer le backlog sauvegardé
        saved_backlog = mock_storage_instance.save_backlog.call_args.args[1]

        # 4. Vérifier que le backlog contient toujours 2 items
        assert len(saved_backlog) == 2

        # 5. Vérifier que le premier item a été modifié
        modified_item = next(item for item in saved_backlog if item.id == "TEST-1")
        assert modified_item.title == "Story modifiée"
        assert modified_item.description == "Nouvelle description améliorée"

        # 6. Vérifier que le second item n'a pas été modifié
        unmodified_item = next(item for item in saved_backlog if item.id == "TEST-2")
        assert unmodified_item.title == "Ancienne tâche"
        assert unmodified_item.description == "Ancienne description"
