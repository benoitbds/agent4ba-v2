"""Test agent for generating test cases for work items."""

import json
import os
import uuid
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from litellm import completion

from agent4ba.api.event_queue import get_event_queue
from agent4ba.core.logger import setup_logger
from agent4ba.core.models import TestCase
from agent4ba.core.storage import ProjectContextService

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger = setup_logger(__name__)


def load_generate_test_cases_prompt() -> dict[str, Any]:
    """
    Charge le prompt de génération de cas de test depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "generate_test_cases.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def generate_test_cases(state: Any) -> dict[str, Any]:
    """
    Génère les cas de test pour un Work Item existant.

    Args:
        state: État actuel du graphe contenant project_id, intent avec item_id

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    logger.info("Generating test cases for work item...")

    # Vérifier d'abord si un contexte de type "work_item" est fourni
    context = state.get("context", [])
    item_id = None
    if context:
        for ctx_item in context:
            if ctx_item.get("type") == "work_item":
                item_id = ctx_item.get("id")
                logger.info(f"Work item context provided: {item_id}")
                break

    # Si pas de contexte, récupérer l'item_id depuis intent_args
    if not item_id:
        # Accepter à la fois "work_item_id" et "work_item" pour compatibilité
        intent_args = state.get("intent_args", {})
        item_id = intent_args.get("work_item_id") or intent_args.get("work_item")

    if not item_id:
        logger.warning("No item_id found in context or intent args")
        intent_args = state.get("intent_args", {})
        logger.warning(f"intent_args content: {intent_args}")
        return {
            "status": "error",
            "result": "No item_id provided for test case generation",
        }

    logger.info(f"Item ID: {item_id}")

    # Récupérer le thread_id et la queue d'événements
    thread_id = state.get("thread_id", "")
    event_queue = get_event_queue(thread_id) if thread_id else None

    # Initialiser la liste d'événements
    agent_events = []

    # Émettre l'événement AgentStart
    start_event = {
        "type": "agent_start",
        "thought": f"Je vais générer les cas de test pour le work item {item_id}.",
        "agent_name": "TestAgent",
    }
    agent_events.append(start_event)
    if event_queue:
        event_queue.put(start_event)

    # Émettre le plan d'action
    plan_event = {
        "type": "agent_plan",
        "steps": [
            "Chargement du contexte du projet",
            "Recherche du work item",
            "Génération des cas de test via LLM",
            "Construction de l'ImpactPlan",
        ],
        "agent_name": "TestAgent",
    }
    agent_events.append(plan_event)
    if event_queue:
        event_queue.put(plan_event)

    # Charger le contexte du projet
    project_id = state.get("project_id", "")
    storage = ProjectContextService()

    # Émettre l'événement de chargement du contexte
    load_run_id = str(uuid.uuid4())
    load_event = {
        "type": "tool_used",
        "tool_run_id": load_run_id,
        "tool_name": "Chargement du contexte",
        "tool_icon": "📚",
        "description": "Chargement du backlog existant du projet",
        "status": "running",
        "details": {},
    }
    agent_events.append(load_event)
    if event_queue:
        event_queue.put(load_event)

    try:
        existing_items = storage.load_context(project_id)
        logger.info(f"Loaded {len(existing_items)} existing work items")
        load_event_completed = {
            "type": "tool_used",
            "tool_run_id": load_run_id,
            "tool_name": "Chargement du contexte",
            "tool_icon": "📚",
            "description": "Chargement du backlog existant du projet",
            "status": "completed",
            "details": {"items_count": len(existing_items)},
        }
        agent_events[-1] = load_event_completed
        if event_queue:
            event_queue.put(load_event_completed)
    except FileNotFoundError:
        logger.warning("No existing backlog found")
        load_event_error = {
            "type": "tool_used",
            "tool_run_id": load_run_id,
            "tool_name": "Chargement du contexte",
            "tool_icon": "📚",
            "description": "Chargement du backlog existant du projet",
            "status": "error",
            "details": {"error": f"No backlog found for project {project_id}"},
        }
        agent_events[-1] = load_event_error
        if event_queue:
            event_queue.put(load_event_error)
        return {
            "status": "error",
            "result": f"No backlog found for project {project_id}",
            "agent_events": agent_events,
        }

    # Trouver l'item correspondant
    target_item = None
    for item in existing_items:
        if item.id == item_id:
            target_item = item
            break

    if target_item is None:
        logger.warning(f"Item {item_id} not found in backlog")
        return {
            "status": "error",
            "result": f"Work item {item_id} not found in backlog",
            "agent_events": agent_events,
        }

    logger.info(f"Found item: {target_item.type} - {target_item.title}")
    logger.info(f"Current description: {target_item.description}")
    logger.info(f"Acceptance criteria: {target_item.acceptance_criteria}")

    # Sauvegarder l'état "before"
    item_before = target_item.model_copy(deep=True)

    # Charger le prompt
    prompt_config = load_generate_test_cases_prompt()

    # Formater les critères d'acceptation pour le prompt
    acceptance_criteria_text = "\n".join(
        [f"- {criterion}" for criterion in target_item.acceptance_criteria]
    )
    if not acceptance_criteria_text:
        acceptance_criteria_text = "Aucun critère d'acceptation défini"

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].format(
        title=target_item.title,
        description=target_item.description or "",
        acceptance_criteria=acceptance_criteria_text,
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    logger.info(f"Using model: {model}")

    # Émettre l'événement d'appel LLM
    llm_run_id = str(uuid.uuid4())
    llm_event = {
        "type": "tool_used",
        "tool_run_id": llm_run_id,
        "tool_name": "Appel LLM",
        "tool_icon": "🧠",
        "description": f"Génération des cas de test avec {model}",
        "status": "running",
        "details": {"model": model, "temperature": temperature, "item_id": item_id},
    }
    agent_events.append(llm_event)
    if event_queue:
        event_queue.put(llm_event)

    try:
        # Appeler le LLM
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": prompt_config["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )

        # Extraire la réponse
        response_text = response.choices[0].message.content.strip()

        logger.info(f"LLM response received: {len(response_text)} characters")

        # Parser la réponse JSON
        test_cases_data = json.loads(response_text)

        if not isinstance(test_cases_data, list):
            raise ValueError("LLM response is not a list of test cases")

        logger.info(f"Generated {len(test_cases_data)} test cases")

        # Valider et convertir en TestCase
        test_cases = []
        for i, test_case_data in enumerate(test_cases_data, 1):
            try:
                # Créer le TestCase (validation Pydantic)
                test_case = TestCase(**test_case_data)
                test_cases.append(test_case)
                logger.info(f"  {i}. {test_case.title}")
            except Exception as e:
                logger.warning(f"Failed to parse test case {i}: {e}")
                # Continuer avec les autres cas de test
                continue

        if not test_cases:
            raise ValueError("No valid test cases could be generated")

        # Mettre à jour le statut de l'événement
        llm_event_completed = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Génération des cas de test avec {model}",
            "status": "completed",
            "details": {
                "model": model,
                "temperature": temperature,
                "item_id": item_id,
                "test_cases_count": len(test_cases),
            },
        }
        agent_events[-1] = llm_event_completed
        if event_queue:
            event_queue.put(llm_event_completed)

        # Créer l'état "after" avec les cas de test
        item_after = target_item.model_copy(deep=True)
        item_after.test_cases = test_cases
        # Marquer l'item comme modifié par l'IA
        if item_before.validation_status == "human_validated":
            item_after.validation_status = "ia_modified"
        # Sinon, il garde son statut actuel (ia_generated ou ia_modified)

        # Construire l'ImpactPlan avec modified_items au format {before, after}
        impact_plan = {
            "new_items": [],
            "modified_items": [
                {
                    "before": item_before.model_dump(),
                    "after": item_after.model_dump(),
                }
            ],
            "deleted_items": [],
        }

        logger.info("ImpactPlan created successfully")
        logger.info(f"- 1 modified item with {len(test_cases)} test cases")
        logger.info("Workflow paused, awaiting human approval")

        # Émettre l'événement de construction de l'ImpactPlan
        plan_build_run_id = str(uuid.uuid4())
        plan_build_event = {
            "type": "tool_used",
            "tool_run_id": plan_build_run_id,
            "tool_name": "Construction ImpactPlan",
            "tool_icon": "📋",
            "description": "Création du plan d'impact avec les cas de test générés",
            "status": "completed",
            "details": {"modified_items_count": 1, "test_cases_count": len(test_cases)},
        }
        agent_events.append(plan_build_event)
        if event_queue:
            event_queue.put(plan_build_event)

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Generated {len(test_cases)} test cases for work item: {item_id}",
            "agent_events": agent_events,
        }

    except json.JSONDecodeError as e:
        logger.error("Error parsing JSON from LLM response.", exc_info=True)
        llm_event_error = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Génération des cas de test avec {model}",
            "status": "error",
            "details": {
                "model": model,
                "error": f"JSON parsing error: {str(e)}",
            },
        }
        agent_events[-1] = llm_event_error
        if event_queue:
            event_queue.put(llm_event_error)
        return {
            "status": "error",
            "result": f"Failed to parse LLM response as JSON: {e}",
            "agent_events": agent_events,
        }
    except Exception as e:
        logger.error("Error during test case generation.", exc_info=True)
        llm_event_error = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Génération des cas de test avec {model}",
            "status": "error",
            "details": {
                "model": model,
                "error": str(e),
            },
        }
        agent_events[-1] = llm_event_error
        if event_queue:
            event_queue.put(llm_event_error)
        return {
            "status": "error",
            "result": f"Failed to generate test cases: {e}",
            "agent_events": agent_events,
        }
