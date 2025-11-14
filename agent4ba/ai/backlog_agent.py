"""Backlog agent for managing project backlogs with AI assistance."""

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


def load_decompose_prompt() -> dict[str, Any]:
    """
    Charge le prompt de décomposition depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "decompose_objective.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def load_improve_description_prompt() -> dict[str, Any]:
    """
    Charge le prompt d'amélioration de description depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "improve_description.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def load_invest_analysis_prompt() -> dict[str, Any]:
    """
    Charge le prompt d'analyse INVEST depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "invest_analysis.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def decompose_objective(state: Any) -> dict[str, Any]:
    """
    Décompose un objectif métier en work items structurés.

    Args:
        state: État actuel du graphe contenant project_id, intent avec objective

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    logger.info("Decomposing objective into work items...")

    # Récupérer l'objectif depuis l'intention
    intent = state.get("intent", {})
    objective = intent.get("args", {}).get("objective", "")

    if not objective:
        logger.warning("No objective found in intent args")
        return {
            "status": "error",
            "result": "No objective provided for decomposition",
        }

    logger.info(f"Objective: {objective}")

    # Récupérer le thread_id et la queue d'événements
    thread_id = state.get("thread_id", "")
    event_queue = get_event_queue(thread_id) if thread_id else None

    # Initialiser la liste d'événements (pour compatibilité)
    agent_events = []

    # Émettre l'événement AgentStart avec la reformulation
    start_event = {
        "type": "agent_start",
        "thought": f"Parfait ! Je vais décomposer l'objectif « {objective} » en une structure hiérarchique de fonctionnalités et user stories.",
        "agent_name": "BacklogAgent",
    }
    agent_events.append(start_event)
    if event_queue:
        event_queue.put(start_event)

    # Émettre le plan d'action
    plan_event = {
        "type": "agent_plan",
        "steps": [
            "Chargement du contexte du projet",
            "Analyse de l'objectif métier",
            "Génération de la structure (Features & Stories)",
            "Validation et construction de l'ImpactPlan",
        ],
        "agent_name": "BacklogAgent",
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
        context_summary = f"Backlog actuel avec {len(existing_items)} work items"
        logger.info(f"Loaded {len(existing_items)} existing work items")
        # Mettre à jour le statut
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
        existing_items = []
        context_summary = "Nouveau projet sans backlog existant"
        logger.info("No existing backlog found")
        load_event_completed = {
            "type": "tool_used",
            "tool_run_id": load_run_id,
            "tool_name": "Chargement du contexte",
            "tool_icon": "📚",
            "description": "Chargement du backlog existant du projet",
            "status": "completed",
            "details": {"items_count": 0},
        }
        agent_events[-1] = load_event_completed
        if event_queue:
            event_queue.put(load_event_completed)

    # Charger le prompt
    prompt_config = load_decompose_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].format(
        objective=objective,
        context=context_summary,
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
        "description": f"Génération de la décomposition avec {model}",
        "status": "running",
        "details": {"model": model, "temperature": temperature},
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
            "description": f"Génération de la décomposition avec {model}",
            "status": "completed",
            "details": {
                "model": model,
                "temperature": temperature,
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

        logger.info(f"Generated {len(work_items_data)} work items")

        # Assigner des ID séquentiels uniques basés sur le préfixe du projet
        work_items_data = assign_sequential_ids(project_id, existing_items, work_items_data)
        logger.info("Assigned sequential IDs starting with project prefix")

        # Valider et convertir en WorkItem
        new_items = []
        for item_data in work_items_data:
            # Ajouter le project_id
            item_data["project_id"] = project_id
            # Marquer comme généré par l'IA (utilise la valeur par défaut "ia_generated")
            # Pas besoin de définir explicitement validation_status

            # Créer le WorkItem (validation Pydantic)
            work_item = WorkItem(**item_data)
            new_items.append(work_item)

            logger.info(f"  - {work_item.type}: {work_item.title} (ID: {work_item.id})")

        # Construire l'ImpactPlan
        impact_plan = {
            "new_items": [item.model_dump() for item in new_items],
            "modified_items": [],
            "deleted_items": [],
        }

        logger.info("ImpactPlan created successfully")
        logger.info(f"- {len(new_items)} new items")
        logger.info("Workflow paused, awaiting human approval")

        # Émettre l'événement de construction de l'ImpactPlan
        plan_build_run_id = str(uuid.uuid4())
        plan_build_event = {
            "type": "tool_used",
            "tool_run_id": plan_build_run_id,
            "tool_name": "Construction ImpactPlan",
            "tool_icon": "📋",
            "description": "Création du plan d'impact avec les work items générés",
            "status": "completed",
            "details": {"new_items_count": len(new_items)},
        }
        agent_events.append(plan_build_event)
        if event_queue:
            event_queue.put(plan_build_event)

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Generated {len(new_items)} work items for objective: {objective}",
            "agent_events": agent_events,
        }

    except json.JSONDecodeError as e:
        logger.error("Error parsing JSON.", exc_info=True)
        llm_event_error = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Génération de la décomposition avec {model}",
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
            "result": f"Failed to parse LLM response as JSON: {e}",
            "agent_events": agent_events,
        }
    except Exception as e:
        logger.error("Error during objective decomposition.", exc_info=True)
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
            "result": f"Failed to decompose objective: {e}",
            "agent_events": agent_events,
        }


def improve_description(state: Any) -> dict[str, Any]:
    """
    Améliore la description d'un work item existant.

    Args:
        state: État actuel du graphe contenant project_id, intent avec item_id

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    logger.info("Improving work item description...")

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
            "result": "No item_id provided for description improvement",
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
        "thought": f"Je vais améliorer la description du work item {item_id}.",
        "agent_name": "BacklogAgent",
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
            "Amélioration de la description via LLM",
            "Construction de l'ImpactPlan",
        ],
        "agent_name": "BacklogAgent",
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

    # Sauvegarder l'état "before"
    item_before = target_item.model_copy(deep=True)

    # Charger le prompt
    prompt_config = load_improve_description_prompt()

    # Préparer le contexte du projet
    context_summary = f"Projet avec {len(existing_items)} work items dans le backlog"

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].format(
        item_type=target_item.type,
        item_title=target_item.title,
        current_description=target_item.description or "",
        context=context_summary,
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
        "description": f"Amélioration de la description avec {model}",
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
        improved_description = response.choices[0].message.content.strip()

        logger.info(f"LLM response received: {len(improved_description)} characters")
        logger.info(f"Improved description: {improved_description}")

        # Mettre à jour le statut
        llm_event_completed = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Amélioration de la description avec {model}",
            "status": "completed",
            "details": {
                "model": model,
                "temperature": temperature,
                "item_id": item_id,
                "response_length": len(improved_description),
            },
        }
        agent_events[-1] = llm_event_completed
        if event_queue:
            event_queue.put(llm_event_completed)

        # Créer l'état "after" avec la nouvelle description
        item_after = target_item.model_copy(deep=True)
        item_after.description = improved_description
        # Si l'item était validé par un humain, le marquer comme modifié par l'IA
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
        logger.info("- 1 modified item")
        logger.info("Workflow paused, awaiting human approval")

        # Émettre l'événement de construction de l'ImpactPlan
        plan_build_run_id = str(uuid.uuid4())
        plan_build_event = {
            "type": "tool_used",
            "tool_run_id": plan_build_run_id,
            "tool_name": "Construction ImpactPlan",
            "tool_icon": "📋",
            "description": "Création du plan d'impact avec la description améliorée",
            "status": "completed",
            "details": {"modified_items_count": 1},
        }
        agent_events.append(plan_build_event)
        if event_queue:
            event_queue.put(plan_build_event)

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Improved description for work item: {item_id}",
            "agent_events": agent_events,
        }

    except Exception as e:
        logger.error("Error during description improvement.", exc_info=True)
        llm_event_error = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Appel LLM",
            "tool_icon": "🧠",
            "description": f"Amélioration de la description avec {model}",
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
            "result": f"Failed to improve description: {e}",
            "agent_events": agent_events,
        }


def review_quality(state: Any) -> dict[str, Any]:
    """
    Analyse la qualité des User Stories du backlog selon les critères INVEST.

    Args:
        state: État actuel du graphe contenant project_id

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    logger.info("Reviewing backlog quality with INVEST criteria...")

    # Récupérer le thread_id et la queue d'événements
    thread_id = state.get("thread_id", "")
    event_queue = get_event_queue(thread_id) if thread_id else None

    # Initialiser la liste d'événements
    agent_events = []

    # Émettre l'événement AgentStart
    start_event = {
        "type": "agent_start",
        "thought": "Je vais analyser la qualité des User Stories du backlog selon les critères INVEST.",
        "agent_name": "BacklogAgent",
    }
    agent_events.append(start_event)
    if event_queue:
        event_queue.put(start_event)

    # Émettre le plan d'action
    plan_event = {
        "type": "agent_plan",
        "steps": [
            "Chargement du contexte du projet",
            "Filtrage des User Stories",
            "Analyse INVEST de chaque story",
            "Construction de l'ImpactPlan",
        ],
        "agent_name": "BacklogAgent",
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

    # Filtrer uniquement les stories (pas les features ni les tasks)
    stories = [item for item in existing_items if item.type == "story"]

    if len(stories) == 0:
        logger.info("No user stories found in backlog")
        return {
            "status": "completed",
            "result": "No user stories found in backlog to analyze",
            "agent_events": agent_events,
        }

    logger.info(f"Found {len(stories)} user stories to analyze")

    # Charger le prompt
    prompt_config = load_invest_analysis_prompt()

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    logger.info(f"Using model: {model}")

    # Préparer le contexte du projet
    context_summary = f"Projet avec {len(existing_items)} work items dans le backlog ({len(stories)} user stories)"

    modified_items = []

    # Analyser chaque story
    for story in stories:
        logger.info(f"Analyzing story: {story.id} - {story.title}")

        # Sauvegarder l'état "before"
        item_before = story.model_copy(deep=True)

        # Préparer le prompt utilisateur
        user_prompt = prompt_config["user_prompt_template"].format(
            title=story.title,
            description=story.description or "",
            context=context_summary,
        )

        # Émettre l'événement d'appel LLM pour cette story
        llm_run_id = str(uuid.uuid4())
        llm_event = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Analyse INVEST",
            "tool_icon": "🔍",
            "description": f"Analyse de la story: {story.title[:50]}...",
            "status": "running",
            "details": {"model": model, "story_id": story.id},
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

            logger.info(f"LLM response received for {story.id}")

            # Parser la réponse JSON
            analysis_result = json.loads(response_text)

            if "invest_analysis" not in analysis_result:
                logger.warning(f"No 'invest_analysis' in response for {story.id}")
                llm_event_error = {
                    "type": "tool_used",
                    "tool_run_id": llm_run_id,
                    "tool_name": "Analyse INVEST",
                    "tool_icon": "🔍",
                    "description": f"Analyse de la story: {story.title[:50]}...",
                    "status": "error",
                    "details": {
                        "model": model,
                        "story_id": story.id,
                        "error": "No 'invest_analysis' in response",
                    },
                }
                agent_events[-1] = llm_event_error
                if event_queue:
                    event_queue.put(llm_event_error)
                continue

            invest_analysis = analysis_result["invest_analysis"]

            logger.info(f"INVEST scores for {story.id}:")
            for criterion, data in invest_analysis.items():
                logger.info(f"  {criterion}: {data['score']:.2f} - {data['reason']}")

            # Calculer le score moyen
            avg_score = sum(data["score"] for data in invest_analysis.values()) / len(invest_analysis)

            # Mettre à jour le statut de l'événement
            llm_event_completed = {
                "type": "tool_used",
                "tool_run_id": llm_run_id,
                "tool_name": "Analyse INVEST",
                "tool_icon": "🔍",
                "description": f"Analyse de la story: {story.title[:50]}...",
                "status": "completed",
                "details": {
                    "model": model,
                    "story_id": story.id,
                    "average_score": round(avg_score, 2),
                },
            }
            agent_events[-1] = llm_event_completed
            if event_queue:
                event_queue.put(llm_event_completed)

            # Créer l'état "after" avec l'analyse INVEST dans les attributes
            item_after = story.model_copy(deep=True)
            item_after.attributes["invest_analysis"] = invest_analysis
            # Si l'item était validé par un humain, le marquer comme modifié par l'IA
            if item_before.validation_status == "human_validated":
                item_after.validation_status = "ia_modified"
            # Sinon, il garde son statut actuel (ia_generated ou ia_modified)

            # Ajouter à la liste des items modifiés
            modified_items.append({
                "before": item_before.model_dump(),
                "after": item_after.model_dump(),
            })

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON for {story.id}.", exc_info=True)
            llm_event_error = {
                "type": "tool_used",
                "tool_run_id": llm_run_id,
                "tool_name": "Analyse INVEST",
                "tool_icon": "🔍",
                "description": f"Analyse de la story: {story.title[:50]}...",
                "status": "error",
                "details": {
                    "model": model,
                    "story_id": story.id,
                    "error": f"JSON parsing error: {str(e)}",
                },
            }
            agent_events[-1] = llm_event_error
            if event_queue:
                event_queue.put(llm_event_error)
            continue
        except Exception as e:
            logger.error(f"Error analyzing {story.id}.", exc_info=True)
            llm_event_error = {
                "type": "tool_used",
                "tool_run_id": llm_run_id,
                "tool_name": "Analyse INVEST",
                "tool_icon": "🔍",
                "description": f"Analyse de la story: {story.title[:50]}...",
                "status": "error",
                "details": {
                    "model": model,
                    "story_id": story.id,
                    "error": str(e),
                },
            }
            agent_events[-1] = llm_event_error
            if event_queue:
                event_queue.put(llm_event_error)
            continue

    if len(modified_items) == 0:
        logger.warning("No stories were successfully analyzed")
        return {
            "status": "error",
            "result": "Failed to analyze any stories",
            "agent_events": agent_events,
        }

    # Construire l'ImpactPlan avec modified_items
    impact_plan = {
        "new_items": [],
        "modified_items": modified_items,
        "deleted_items": [],
    }

    logger.info("ImpactPlan created successfully")
    logger.info(f"- {len(modified_items)} stories analyzed with INVEST criteria")
    logger.info("Workflow paused, awaiting human approval")

    # Émettre l'événement de construction de l'ImpactPlan
    plan_build_run_id = str(uuid.uuid4())
    plan_build_event = {
        "type": "tool_used",
        "tool_run_id": plan_build_run_id,
        "tool_name": "Construction ImpactPlan",
        "tool_icon": "📋",
        "description": "Création du plan d'impact avec les analyses INVEST",
        "status": "completed",
        "details": {"analyzed_stories_count": len(modified_items)},
    }
    agent_events.append(plan_build_event)
    if event_queue:
        event_queue.put(plan_build_event)

    return {
        "impact_plan": impact_plan,
        "status": "awaiting_approval",
        "result": f"Analyzed {len(modified_items)} user stories with INVEST criteria",
        "agent_events": agent_events,
    }
