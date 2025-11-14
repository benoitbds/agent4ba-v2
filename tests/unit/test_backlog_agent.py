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
            assert item["validation_status"] == "ia_generated"

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


def test_decompose_objective_llm_error():
    """
    Test de decompose_objective lorsque le LLM lève une exception.

    Vérifie que la fonction gère correctement les erreurs LLM en retournant
    un état avec status "error" et un message d'erreur approprié.
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

    # Appliquer les patches
    with patch('agent4ba.ai.backlog_agent.completion', side_effect=Exception("LLM service unavailable")) as mock_completion, \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None):

        # Configurer le mock du storage pour retourner une liste vide
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = []
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.decompose_objective(state)

        # Vérifications
        assert result is not None
        assert "status" in result
        assert result["status"] == "error"
        assert "result" in result
        assert "Failed to decompose objective" in result["result"]
        assert "LLM service unavailable" in result["result"]
        # Vérifier qu'aucun impact_plan n'a été créé
        assert "impact_plan" not in result or result.get("impact_plan") is None


def test_decompose_objective_json_parse_error():
    """
    Test de decompose_objective lorsque le LLM retourne un JSON invalide.

    Vérifie que la fonction gère correctement les erreurs de parsing JSON
    en retournant un état avec status "error".
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

    # Créer le mock de la réponse LLM avec du JSON invalide
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = "Ceci n'est pas du JSON valide { invalid"

    # Appliquer les patches
    with patch('agent4ba.ai.backlog_agent.completion', return_value=mock_llm_response), \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None):

        # Configurer le mock du storage pour retourner une liste vide
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = []
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.decompose_objective(state)

        # Vérifications
        assert result is not None
        assert "status" in result
        assert result["status"] == "error"
        assert "result" in result
        assert "Failed to parse LLM response as JSON" in result["result"]
        # Vérifier qu'aucun impact_plan n'a été créé
        assert "impact_plan" not in result or result.get("impact_plan") is None


def test_decompose_objective_no_objective():
    """
    Test de decompose_objective lorsque aucun objectif n'est fourni.

    Vérifie que la fonction se termine gracieusement sans créer d'ImpactPlan
    lorsque la clé objective est absente ou vide.
    """
    # Créer un state sans objectif
    state = {
        "project_id": "TEST",
        "intent": {
            "args": {}  # Pas de clé objective
        },
        "thread_id": "test-thread-123"
    }

    # Appliquer les patches (bien que le LLM ne devrait pas être appelé)
    with patch('agent4ba.ai.backlog_agent.completion') as mock_completion, \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None):

        # Configurer le mock du storage pour retourner une liste vide
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = []
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.decompose_objective(state)

        # Vérifications
        assert result is not None
        assert "status" in result
        assert result["status"] == "error"
        assert "result" in result
        assert "No objective provided" in result["result"]
        # Vérifier que le LLM n'a pas été appelé
        mock_completion.assert_not_called()
        # Vérifier qu'aucun impact_plan n'a été créé
        assert "impact_plan" not in result or result.get("impact_plan") is None


def test_improve_description_success():
    """
    Test du cas nominal de la fonction improve_description.

    Vérifie que la fonction améliore correctement la description d'un work item
    existant et retourne un ImpactPlan avec une opération de type update.
    """
    # Préparer le state initial avec un item_id
    state = {
        "project_id": "TEST",
        "intent": {},
        "intent_args": {
            "work_item_id": "TEST-1"
        },
        "thread_id": "test-thread-123"
    }

    # Créer un WorkItem existant à améliorer
    from agent4ba.core.models import WorkItem
    existing_item = WorkItem(
        id="TEST-1",
        project_id="TEST",
        type="story",
        title="Formulaire de connexion",
        description="Description basique",
        parent_id=None,
        attributes={}
    )

    # Créer le mock de la réponse LLM avec la nouvelle description
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = "En tant qu'utilisateur, je veux me connecter avec mon email et mot de passe pour accéder à mon compte de manière sécurisée."

    # Appliquer les patches
    with patch('agent4ba.ai.backlog_agent.completion', return_value=mock_llm_response), \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None):

        # Configurer le mock du storage pour retourner l'item existant
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = [existing_item]
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.improve_description(state)

        # Vérifications
        assert result is not None
        assert "impact_plan" in result
        assert result["impact_plan"] is not None

        impact_plan = result["impact_plan"]
        assert "modified_items" in impact_plan
        assert isinstance(impact_plan["modified_items"], list)
        assert len(impact_plan["modified_items"]) == 1

        # Vérifier la structure de l'opération de modification
        modified_item = impact_plan["modified_items"][0]
        assert "before" in modified_item
        assert "after" in modified_item

        # Vérifier que la description a été modifiée
        assert modified_item["before"]["description"] == "Description basique"
        assert modified_item["after"]["description"] != "Description basique"
        assert "En tant qu'utilisateur" in modified_item["after"]["description"]

        # Vérifier que le validation_status reste "ia_generated" (car l'item n'était pas validé)
        assert modified_item["before"]["validation_status"] == "ia_generated"
        assert modified_item["after"]["validation_status"] == "ia_generated"

        # Vérifier le statut de retour
        assert result["status"] == "awaiting_approval"

        # Vérifier que new_items et deleted_items sont vides
        assert impact_plan["new_items"] == []
        assert impact_plan["deleted_items"] == []


def test_improve_description_item_not_found():
    """
    Test de improve_description lorsque le work item n'est pas trouvé.

    Vérifie que la fonction gère correctement le cas où l'item_id fourni
    ne correspond à aucun work item dans le backlog.
    """
    # Préparer le state initial avec un item_id inexistant
    state = {
        "project_id": "TEST",
        "intent": {},
        "intent_args": {
            "work_item_id": "TEST-999"  # ID qui n'existe pas
        },
        "thread_id": "test-thread-123"
    }

    # Créer un WorkItem existant (mais pas celui recherché)
    from agent4ba.core.models import WorkItem
    existing_item = WorkItem(
        id="TEST-1",
        project_id="TEST",
        type="story",
        title="Autre story",
        description="Description",
        parent_id=None,
        attributes={}
    )

    # Appliquer les patches
    with patch('agent4ba.ai.backlog_agent.completion') as mock_completion, \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None):

        # Configurer le mock du storage pour retourner un item différent
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = [existing_item]
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.improve_description(state)

        # Vérifications
        assert result is not None
        assert "status" in result
        assert result["status"] == "error"
        assert "result" in result
        assert "TEST-999" in result["result"]
        assert "not found" in result["result"]

        # Vérifier que le LLM n'a pas été appelé
        mock_completion.assert_not_called()

        # Vérifier qu'aucun impact_plan n'a été créé
        assert "impact_plan" not in result or result.get("impact_plan") is None


def test_review_quality_success():
    """
    Test du cas nominal de la fonction review_quality.

    Vérifie que la fonction analyse correctement la qualité des User Stories
    selon les critères INVEST et retourne un ImpactPlan avec les scores ajoutés.
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "intent": {},
        "thread_id": "test-thread-123"
    }

    # Créer plusieurs User Stories existantes
    from agent4ba.core.models import WorkItem
    story1 = WorkItem(
        id="TEST-1",
        project_id="TEST",
        type="story",
        title="Connexion utilisateur",
        description="En tant qu'utilisateur, je veux me connecter",
        parent_id=None,
        attributes={}
    )
    story2 = WorkItem(
        id="TEST-2",
        project_id="TEST",
        type="story",
        title="Déconnexion",
        description="En tant qu'utilisateur, je veux me déconnecter",
        parent_id=None,
        attributes={}
    )
    feature1 = WorkItem(
        id="TEST-3",
        project_id="TEST",
        type="feature",
        title="Authentification",
        description="Feature d'authentification",
        parent_id=None,
        attributes={}
    )

    # Préparer le mock de l'analyse INVEST
    mock_invest_analysis = {
        "invest_analysis": {
            "Independent": {"score": 0.9, "reason": "La story est indépendante"},
            "Negotiable": {"score": 0.8, "reason": "La story est négociable"},
            "Valuable": {"score": 0.95, "reason": "La story apporte de la valeur"},
            "Estimable": {"score": 0.85, "reason": "La story est estimable"},
            "Small": {"score": 0.7, "reason": "La story est relativement petite"},
            "Testable": {"score": 0.9, "reason": "La story est testable"}
        }
    }

    # Créer le mock de la réponse LLM
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = json.dumps(mock_invest_analysis)

    # Appliquer les patches
    with patch('agent4ba.ai.backlog_agent.completion', return_value=mock_llm_response), \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None):

        # Configurer le mock du storage pour retourner les items (2 stories + 1 feature)
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = [story1, story2, feature1]
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.review_quality(state)

        # Vérifications
        assert result is not None
        assert "impact_plan" in result
        assert result["impact_plan"] is not None

        impact_plan = result["impact_plan"]
        assert "modified_items" in impact_plan
        assert isinstance(impact_plan["modified_items"], list)
        # Seules les 2 stories doivent être analysées (pas la feature)
        assert len(impact_plan["modified_items"]) == 2

        # Vérifier la structure de chaque modification
        for modified_item in impact_plan["modified_items"]:
            assert "before" in modified_item
            assert "after" in modified_item

            # Vérifier que l'analyse INVEST a été ajoutée dans les attributes
            assert "invest_analysis" not in modified_item["before"]["attributes"]
            assert "invest_analysis" in modified_item["after"]["attributes"]

            invest_analysis = modified_item["after"]["attributes"]["invest_analysis"]
            assert "Independent" in invest_analysis
            assert "Negotiable" in invest_analysis
            assert "Valuable" in invest_analysis
            assert "Estimable" in invest_analysis
            assert "Small" in invest_analysis
            assert "Testable" in invest_analysis

            # Vérifier que chaque critère a un score et une raison
            for criterion, data in invest_analysis.items():
                assert "score" in data
                assert "reason" in data
                assert isinstance(data["score"], (int, float))
                assert isinstance(data["reason"], str)

            # Vérifier que le validation_status reste "ia_generated" (car l'item n'était pas validé)
            assert modified_item["before"]["validation_status"] == "ia_generated"
            assert modified_item["after"]["validation_status"] == "ia_generated"

        # Vérifier le statut de retour
        assert result["status"] == "awaiting_approval"

        # Vérifier que new_items et deleted_items sont vides
        assert impact_plan["new_items"] == []
        assert impact_plan["deleted_items"] == []


def test_generate_acceptance_criteria_success():
    """
    Test du cas nominal de la fonction generate_acceptance_criteria.

    Vérifie que la fonction génère correctement les critères d'acceptation
    pour un WorkItem existant et retourne un ImpactPlan avec une opération de type update.
    """
    # Préparer le state initial avec un item_id
    state = {
        "project_id": "TEST",
        "intent": {},
        "intent_args": {
            "work_item_id": "TEST-1"
        },
        "thread_id": "test-thread-123"
    }

    # Créer un WorkItem existant
    from agent4ba.core.models import WorkItem
    existing_item = WorkItem(
        id="TEST-1",
        project_id="TEST",
        type="story",
        title="Page de connexion utilisateur",
        description="En tant qu'utilisateur, je veux pouvoir me connecter à mon compte avec mon email et mot de passe afin d'accéder à mes données personnelles et fonctionnalités sécurisées",
        parent_id=None,
        attributes={}
    )

    # Créer le mock de la réponse LLM avec les critères d'acceptation
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = """- L'utilisateur peut saisir son email et son mot de passe dans les champs dédiés
- Un bouton "Se connecter" est visible et cliquable
- En cas de succès, l'utilisateur est redirigé vers le tableau de bord
- Un message d'erreur s'affiche si l'email ou le mot de passe est incorrect
- Un message d'erreur s'affiche si l'email n'est pas au format valide
- Le champ mot de passe masque les caractères saisis
- Un lien "Mot de passe oublié ?" est accessible
- Après 3 tentatives échouées, le compte est temporairement verrouillé"""

    # Appliquer les patches
    with patch('agent4ba.ai.backlog_agent.completion', return_value=mock_llm_response), \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None):

        # Configurer le mock du storage pour retourner l'item existant
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = [existing_item]
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.generate_acceptance_criteria(state)

        # Vérifications
        assert result is not None
        assert "impact_plan" in result
        assert result["impact_plan"] is not None

        impact_plan = result["impact_plan"]
        assert "modified_items" in impact_plan
        assert isinstance(impact_plan["modified_items"], list)
        assert len(impact_plan["modified_items"]) == 1

        # Vérifier la structure de l'opération de modification
        modified_item = impact_plan["modified_items"][0]
        assert "before" in modified_item
        assert "after" in modified_item

        # Vérifier que les critères d'acceptation ont été ajoutés
        assert "acceptance_criteria" in modified_item["after"]
        acceptance_criteria = modified_item["after"]["acceptance_criteria"]
        assert isinstance(acceptance_criteria, list)
        assert len(acceptance_criteria) == 8  # 8 critères dans le mock

        # Vérifier quelques critères spécifiques
        assert "L'utilisateur peut saisir son email et son mot de passe dans les champs dédiés" in acceptance_criteria
        assert "Un bouton \"Se connecter\" est visible et cliquable" in acceptance_criteria
        assert "Après 3 tentatives échouées, le compte est temporairement verrouillé" in acceptance_criteria

        # Vérifier que le validation_status reste "ia_generated" (car l'item n'était pas validé)
        assert modified_item["before"]["validation_status"] == "ia_generated"
        assert modified_item["after"]["validation_status"] == "ia_generated"

        # Vérifier que l'item "before" n'avait pas de critères d'acceptation
        assert modified_item["before"]["acceptance_criteria"] == []

        # Vérifier le statut de retour
        assert result["status"] == "awaiting_approval"

        # Vérifier que new_items et deleted_items sont vides
        assert impact_plan["new_items"] == []
        assert impact_plan["deleted_items"] == []


def test_generate_acceptance_criteria_item_not_found():
    """
    Test de generate_acceptance_criteria lorsque le work item n'est pas trouvé.

    Vérifie que la fonction gère correctement le cas où l'item_id fourni
    ne correspond à aucun work item dans le backlog.
    """
    # Préparer le state initial avec un item_id inexistant
    state = {
        "project_id": "TEST",
        "intent": {},
        "intent_args": {
            "work_item_id": "TEST-999"  # ID qui n'existe pas
        },
        "thread_id": "test-thread-123"
    }

    # Créer un WorkItem existant (mais pas celui recherché)
    from agent4ba.core.models import WorkItem
    existing_item = WorkItem(
        id="TEST-1",
        project_id="TEST",
        type="story",
        title="Autre story",
        description="Description",
        parent_id=None,
        attributes={}
    )

    # Appliquer les patches
    with patch('agent4ba.ai.backlog_agent.completion') as mock_completion, \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None):

        # Configurer le mock du storage pour retourner un item différent
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = [existing_item]
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.generate_acceptance_criteria(state)

        # Vérifications
        assert result is not None
        assert "status" in result
        assert result["status"] == "error"
        assert "result" in result
        assert "TEST-999" in result["result"]
        assert "not found" in result["result"]

        # Vérifier que le LLM n'a pas été appelé
        mock_completion.assert_not_called()

        # Vérifier qu'aucun impact_plan n'a été créé
        assert "impact_plan" not in result or result.get("impact_plan") is None


def test_generate_acceptance_criteria_human_validated_item():
    """
    Test de generate_acceptance_criteria pour un item déjà validé par un humain.

    Vérifie que le validation_status passe à "ia_modified" lorsque
    l'item était précédemment "human_validated".
    """
    # Préparer le state initial
    state = {
        "project_id": "TEST",
        "intent": {},
        "intent_args": {
            "work_item_id": "TEST-1"
        },
        "thread_id": "test-thread-123"
    }

    # Créer un WorkItem déjà validé par un humain
    from agent4ba.core.models import WorkItem
    existing_item = WorkItem(
        id="TEST-1",
        project_id="TEST",
        type="story",
        title="Story validée",
        description="Description validée par un humain",
        parent_id=None,
        attributes={},
        validation_status="human_validated"  # Item déjà validé
    )

    # Créer le mock de la réponse LLM
    mock_llm_response = Mock()
    mock_llm_response.choices = [Mock()]
    mock_llm_response.choices[0].message = Mock()
    mock_llm_response.choices[0].message.content = """- Critère 1
- Critère 2
- Critère 3"""

    # Appliquer les patches
    with patch('agent4ba.ai.backlog_agent.completion', return_value=mock_llm_response), \
         patch('agent4ba.ai.backlog_agent.ProjectContextService') as mock_storage_class, \
         patch('agent4ba.ai.backlog_agent.get_event_queue', return_value=None):

        # Configurer le mock du storage
        mock_storage_instance = Mock()
        mock_storage_instance.load_context.return_value = [existing_item]
        mock_storage_class.return_value = mock_storage_instance

        # Appeler la fonction
        result = backlog_agent.generate_acceptance_criteria(state)

        # Vérifications
        assert result is not None
        assert result["status"] == "awaiting_approval"

        modified_item = result["impact_plan"]["modified_items"][0]

        # Vérifier que le statut passe de "human_validated" à "ia_modified"
        assert modified_item["before"]["validation_status"] == "human_validated"
        assert modified_item["after"]["validation_status"] == "ia_modified"

        # Vérifier que les critères ont été ajoutés
        assert len(modified_item["after"]["acceptance_criteria"]) == 3
