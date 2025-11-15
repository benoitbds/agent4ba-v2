"""Story Teller agent for decomposing features into user stories."""

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
from agent4ba.core.models import WorkItem
from agent4ba.core.storage import ProjectContextService
from agent4ba.core.workitem_utils import assign_sequential_ids

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger = setup_logger(__name__)


def load_decompose_feature_prompt() -> dict[str, Any]:
    """
    Charge le prompt de décomposition de feature depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "decompose_feature.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def decompose_feature_into_stories(state: Any) -> dict[str, Any]:
    """
    Décompose une feature existante en une liste exhaustive de user stories.

    Cet agent a pour unique responsabilité de produire des USER STORIES,
    JAMAIS de features ou de tâches techniques.

    Args:
        state: État actuel du graphe contenant project_id, intent avec feature_id

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    logger.info("Decomposing feature into user stories...")

    # Récupérer le feature_id depuis l'intention
    intent = state.get("intent", {})
    feature_id = intent.get("args", {}).get("feature_id", "")

    if not feature_id:
        logger.warning("No feature_id found in intent args")
        return {
            "status": "error",
            "result": "No feature_id provided for decomposition",
        }

    logger.info(f"Feature ID: {feature_id}")

    # Récupérer le thread_id et la queue d'événements
    thread_id = state.get("thread_id", "")
    event_queue = get_event_queue(thread_id) if thread_id else None

    # Initialiser la liste d'événements
    agent_events = []

    # Émettre l'événement AgentStart
    start_event = {
        "type": "agent_start",
        "thought": f"Parfait ! Je vais décomposer la feature {feature_id} en user stories détaillées.",
        "agent_name": "StoryTellerAgent",
    }
    agent_events.append(start_event)
    if event_queue:
        event_queue.put(start_event)

    # Émettre le plan d'action
    plan_event = {
        "type": "agent_plan",
        "steps": [
            "Chargement du contexte du projet",
            "Recherche de la feature parente",
            "Analyse de la feature pour identifier les user stories",
            "Génération des user stories exhaustives",
            "Validation et construction de l'ImpactPlan",
        ],
        "agent_name": "StoryTellerAgent",
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

    # Trouver la feature parente
    target_feature = None
    for item in existing_items:
        if item.id == feature_id:
            target_feature = item
            break

    if target_feature is None:
        logger.warning(f"Feature {feature_id} not found in backlog")
        return {
            "status": "error",
            "result": f"Feature {feature_id} not found in backlog",
            "agent_events": agent_events,
        }

    # Vérifier que c'est bien une feature
    if target_feature.type != "feature":
        logger.warning(f"Item {feature_id} is not a feature, it's a {target_feature.type}")
        return {
            "status": "error",
            "result": f"Item {feature_id} is not a feature (type: {target_feature.type})",
            "agent_events": agent_events,
        }

    logger.info(f"Found feature: {target_feature.title}")
    logger.info(f"Feature description: {target_feature.description}")

    # Charger le prompt
    prompt_config = load_decompose_feature_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].format(
        feature_title=target_feature.title,
        feature_description=target_feature.description or "",
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
        "description": f"Génération des user stories avec {model}",
        "status": "running",
        "details": {"model": model, "temperature": temperature, "feature_id": feature_id},
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
        response_text = response.choices[0].message.content

        logger.info(f"LLM response received: {len(response_text)} characters")

        # Mettre à jour le statut
        llm_event_completed = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Génération des user stories avec {model}",
            "status": "completed",
            "details": {
                "model": model,
                "temperature": temperature,
                "feature_id": feature_id,
                "response_length": len(response_text),
            },
        }
        agent_events[-1] = llm_event_completed
        if event_queue:
            event_queue.put(llm_event_completed)

        # Parser la réponse JSON
        work_items_data = json.loads(response_text)

        if not isinstance(work_items_data, list):
            raise ValueError("LLM response is not a list of work items")

        logger.info(f"Generated {len(work_items_data)} user stories")

        # Vérifier que tous les items sont bien des stories
        non_story_items = [item for item in work_items_data if item.get("type") != "story"]
        if non_story_items:
            logger.warning(f"Found {len(non_story_items)} non-story items in response")
            for item in non_story_items:
                logger.warning(f"  - {item.get('type')}: {item.get('title')}")

        # Assigner des ID séquentiels uniques basés sur le préfixe du projet
        work_items_data = assign_sequential_ids(project_id, existing_items, work_items_data)
        logger.info("Assigned sequential IDs starting with project prefix")

        # Valider et convertir en WorkItem
        new_items = []
        for item_data in work_items_data:
            # Ajouter le project_id
            item_data["project_id"] = project_id
            # Définir le parent_id = feature_id pour établir la relation
            item_data["parent_id"] = feature_id
            # Marquer comme généré par l'IA (utilise la valeur par défaut "ia_generated")

            # Créer le WorkItem (validation Pydantic)
            work_item = WorkItem(**item_data)
            new_items.append(work_item)

            logger.info(f"  - {work_item.type}: {work_item.title} (ID: {work_item.id}, Parent: {work_item.parent_id})")

        # Construire l'ImpactPlan
        impact_plan = {
            "new_items": [item.model_dump() for item in new_items],
            "modified_items": [],
            "deleted_items": [],
        }

        logger.info("ImpactPlan created successfully")
        logger.info(f"- {len(new_items)} new user stories")
        logger.info(f"- All stories are children of feature {feature_id}")
        logger.info("Workflow paused, awaiting human approval")

        # Émettre l'événement de construction de l'ImpactPlan
        plan_build_run_id = str(uuid.uuid4())
        plan_build_event = {
            "type": "tool_used",
            "tool_run_id": plan_build_run_id,
            "tool_name": "Construction ImpactPlan",
            "tool_icon": "📋",
            "description": "Création du plan d'impact avec les user stories générées",
            "status": "completed",
            "details": {
                "new_items_count": len(new_items),
                "parent_feature_id": feature_id,
            },
        }
        agent_events.append(plan_build_event)
        if event_queue:
            event_queue.put(plan_build_event)

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Generated {len(new_items)} user stories for feature {feature_id}: {target_feature.title}",
            "agent_events": agent_events,
        }

    except json.JSONDecodeError as e:
        logger.error("Error parsing JSON.", exc_info=True)
        llm_event_error = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Génération des user stories avec {model}",
            "status": "error",
            "details": {
                "model": model,
                "feature_id": feature_id,
                "error": str(e),
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
        logger.error("Error during feature decomposition.", exc_info=True)
        if agent_events and agent_events[-1].get("status") == "running":
            error_event = agent_events[-1].copy()
            error_event["status"] = "error"
            error_event["details"] = error_event.get("details", {})
            error_event["details"]["error"] = str(e)
            agent_events[-1] = error_event
            if event_queue:
                event_queue.put(error_event)
        return {
            "status": "error",
            "result": f"Failed to decompose feature: {e}",
            "agent_events": agent_events,
        }
