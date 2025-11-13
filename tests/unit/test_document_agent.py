"""Tests unitaires pour le module document_agent."""

import json
from unittest.mock import Mock, patch

import pytest

from agent4ba.ai import document_agent


def test_extract_requirements_success():
    """
    Test du cas nominal de la fonction extract_requirements.

    Vérifie que la fonction extrait correctement les exigences à partir de documents
    récupérés via RAG et retourne un ImpactPlan avec les WorkItems générés.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "user_query": "Quelles sont les exigences pour le système d'authentification?",
        "thread_id": "test-thread-123",
    }

    # Préparer les documents fictifs que le retriever devrait retourner
    mock_docs = []
    # Créer 3 documents avec page_content et metadata
    for i in range(1, 4):
        mock_doc = Mock()
        mock_doc.page_content = f"Le système doit permettre l'authentification utilisateur via email et mot de passe. Chunk {i}."
        mock_doc.metadata = {"source": f"requirements_doc_{i}.pdf", "page": i}
        mock_docs.append(mock_doc)

    # Préparer les work items que le LLM devrait retourner
    mock_work_items = [
        {
            "id": "TEST-1",
            "project_id": "TEST",
            "type": "feature",
            "title": "Système d'authentification",
            "description": "Implémenter un système complet d'authentification utilisateur",
            "parent_id": None,
            "attributes": {},
        },
        {
            "id": "TEST-2",
            "project_id": "TEST",
            "type": "story",
            "title": "Connexion par email",
            "description": "En tant qu'utilisateur, je veux me connecter avec mon email et mot de passe",
            "parent_id": "TEST-1",
            "attributes": {},
        },
    ]

    # Créer le mock de la réponse LLM
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = json.dumps(mock_work_items)

    # Créer le mock du prompt config
    mock_prompt_config = {
        "system_prompt": "You are a requirements extraction assistant.",
        "user_prompt_template": "Context: {context}\n\nQuery: {query}\n\nBacklog: {backlog_summary}",
    }

    # Appliquer les patches
    with (
        patch("agent4ba.ai.document_agent.completion", return_value=mock_llm_response) as mock_completion,
        patch("agent4ba.ai.document_agent.DocumentIngestionService") as mock_ingestion_class,
        patch("agent4ba.ai.document_agent.ProjectContextService") as mock_storage_class,
        patch("agent4ba.ai.document_agent.get_event_queue", return_value=None),
        patch("agent4ba.ai.document_agent.assign_sequential_ids", side_effect=lambda proj_id, existing, items: items),
        patch("agent4ba.ai.document_agent.load_extract_requirements_prompt", return_value=mock_prompt_config),
    ):
        # Configurer le mock du vectorstore et retriever
        mock_vectorstore = Mock()
        mock_vectorstore.docstore = Mock()
        mock_vectorstore.docstore._dict = {f"doc_{i}": f"content_{i}" for i in range(10)}

        mock_retriever = Mock()
        mock_retriever.invoke.return_value = mock_docs

        mock_vectorstore.as_retriever.return_value = mock_retriever

        # Configurer le mock du service d'ingestion
        mock_ingestion_instance = Mock()
        mock_ingestion_instance.get_vectorstore.return_value = mock_vectorstore
        mock_ingestion_class.return_value = mock_ingestion_instance

        # Configurer le mock du storage pour retourner une liste vide
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = []
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = document_agent.extract_requirements(state)

        # Vérifications
        # 1. Vérifier que l'impact_plan existe et n'est pas None
        assert result is not None
        assert "impact_plan" in result
        assert result["impact_plan"] is not None

        # 2. Vérifier que l'impact_plan contient une liste de new_items
        impact_plan = result["impact_plan"]
        assert "new_items" in impact_plan
        assert isinstance(impact_plan["new_items"], list)

        # 3. Vérifier le nombre d'items correspond au mock
        assert len(impact_plan["new_items"]) == 2

        # 4. Vérifier que chaque item est un WorkItem avec les champs attendus
        for item in impact_plan["new_items"]:
            assert "id" in item
            assert "type" in item
            assert "title" in item
            assert "description" in item
            assert "project_id" in item
            assert item["project_id"] == "TEST"
            assert item["validation_status"] == "ia_generated"

        # 5. Vérifier le status de retour
        assert result["status"] == "awaiting_approval"

        # 6. Vérifier que le retriever a bien été invoqué
        mock_retriever.invoke.assert_called_once_with(
            "Quelles sont les exigences pour le système d'authentification?"
        )

        # 7. Vérifier que le LLM a bien été appelé
        mock_completion.assert_called_once()

        # 8. Vérifier que modified_items et deleted_items sont vides
        assert impact_plan["modified_items"] == []
        assert impact_plan["deleted_items"] == []


def test_extract_requirements_no_documents_found():
    """
    Test de extract_requirements lorsque le retriever ne trouve aucun document.

    Vérifie que la fonction se comporte correctement lorsque la recherche RAG
    ne retourne aucun document pertinent.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "user_query": "Quelles sont les exigences pour le système d'authentification?",
        "thread_id": "test-thread-123",
    }

    # Le retriever retourne une liste vide de documents
    mock_docs = []

    # Créer le mock du prompt config
    mock_prompt_config = {
        "system_prompt": "You are a requirements extraction assistant.",
        "user_prompt_template": "Context: {context}\n\nQuery: {query}\n\nBacklog: {backlog_summary}",
    }

    # Créer le mock de la réponse LLM (qui ne devrait pas être appelé avec une liste vide)
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = json.dumps([])

    # Appliquer les patches
    with (
        patch("agent4ba.ai.document_agent.completion", return_value=mock_llm_response) as mock_completion,
        patch("agent4ba.ai.document_agent.DocumentIngestionService") as mock_ingestion_class,
        patch("agent4ba.ai.document_agent.ProjectContextService") as mock_storage_class,
        patch("agent4ba.ai.document_agent.get_event_queue", return_value=None),
        patch("agent4ba.ai.document_agent.assign_sequential_ids", side_effect=lambda proj_id, existing, items: items),
        patch("agent4ba.ai.document_agent.load_extract_requirements_prompt", return_value=mock_prompt_config),
    ):
        # Configurer le mock du vectorstore et retriever
        mock_vectorstore = Mock()
        mock_vectorstore.docstore = Mock()
        mock_vectorstore.docstore._dict = {f"doc_{i}": f"content_{i}" for i in range(10)}

        mock_retriever = Mock()
        mock_retriever.invoke.return_value = mock_docs  # Liste vide

        mock_vectorstore.as_retriever.return_value = mock_retriever

        # Configurer le mock du service d'ingestion
        mock_ingestion_instance = Mock()
        mock_ingestion_instance.get_vectorstore.return_value = mock_vectorstore
        mock_ingestion_class.return_value = mock_ingestion_instance

        # Configurer le mock du storage pour retourner une liste vide
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = []
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = document_agent.extract_requirements(state)

        # Vérifications
        # 1. La fonction devrait quand même appeler le LLM (avec un contexte vide)
        # et retourner un ImpactPlan avec 0 items
        assert result is not None

        # 2. Vérifier que le LLM a été appelé même avec des documents vides
        # (Le code actuel appelle toujours le LLM, même sans documents)
        mock_completion.assert_called_once()

        # 3. Vérifier que l'impact_plan existe mais est vide
        assert "impact_plan" in result
        assert result["impact_plan"] is not None
        impact_plan = result["impact_plan"]
        assert len(impact_plan["new_items"]) == 0


def test_extract_requirements_llm_error():
    """
    Test de extract_requirements lorsque le LLM lève une exception.

    Vérifie que la fonction gère correctement les erreurs LLM en retournant
    un état avec status "error" et un message d'erreur approprié.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "user_query": "Quelles sont les exigences pour le système d'authentification?",
        "thread_id": "test-thread-123",
    }

    # Préparer des documents fictifs valides
    mock_docs = []
    for i in range(1, 4):
        mock_doc = Mock()
        mock_doc.page_content = f"Le système doit permettre l'authentification. Chunk {i}."
        mock_doc.metadata = {"source": f"requirements_doc_{i}.pdf", "page": i}
        mock_docs.append(mock_doc)

    # Créer le mock du prompt config
    mock_prompt_config = {
        "system_prompt": "You are a requirements extraction assistant.",
        "user_prompt_template": "Context: {context}\n\nQuery: {query}\n\nBacklog: {backlog_summary}",
    }

    # Appliquer les patches
    with (
        patch(
            "agent4ba.ai.document_agent.completion",
            side_effect=Exception("LLM service unavailable"),
        ) as mock_completion,
        patch("agent4ba.ai.document_agent.DocumentIngestionService") as mock_ingestion_class,
        patch("agent4ba.ai.document_agent.ProjectContextService") as mock_storage_class,
        patch("agent4ba.ai.document_agent.get_event_queue", return_value=None),
        patch("agent4ba.ai.document_agent.load_extract_requirements_prompt", return_value=mock_prompt_config),
    ):
        # Configurer le mock du vectorstore et retriever
        mock_vectorstore = Mock()
        mock_vectorstore.docstore = Mock()
        mock_vectorstore.docstore._dict = {f"doc_{i}": f"content_{i}" for i in range(10)}

        mock_retriever = Mock()
        mock_retriever.invoke.return_value = mock_docs

        mock_vectorstore.as_retriever.return_value = mock_retriever

        # Configurer le mock du service d'ingestion
        mock_ingestion_instance = Mock()
        mock_ingestion_instance.get_vectorstore.return_value = mock_vectorstore
        mock_ingestion_class.return_value = mock_ingestion_instance

        # Configurer le mock du storage pour retourner une liste vide
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = []
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = document_agent.extract_requirements(state)

        # Vérifications
        assert result is not None
        assert "status" in result
        assert result["status"] == "error"
        assert "result" in result
        assert "Failed to extract requirements" in result["result"]
        assert "LLM service unavailable" in result["result"]

        # Vérifier qu'aucun impact_plan n'a été créé
        assert "impact_plan" not in result or result.get("impact_plan") is None

        # Vérifier que le LLM a bien été appelé (mais a échoué)
        mock_completion.assert_called_once()
