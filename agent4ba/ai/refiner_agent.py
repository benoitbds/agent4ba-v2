"""Refiner agent for refining existing backlogs with new information."""

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
from agent4ba.utils.json_parser import JSONParsingError, extract_and_parse_json

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger = setup_logger(__name__)


def load_refine_backlog_prompt() -> dict[str, Any]:
    """
    Charge le prompt de raffinement de backlog depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "refine_backlog.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def refine_backlog(state: Any) -> dict[str, Any]:
    """
    Raffine un backlog existant en fonction d'une nouvelle directive.

    Cette méthode privilégie la modification des items existants plutôt que
    leur suppression et recréation. Elle analyse chaque work item existant
    pour déterminer s'il doit être modifié, supprimé ou conservé tel quel,
    et ne crée de nouveaux items que si la directive introduit des concepts
    entièrement nouveaux.

    Args:
        state: État actuel du graphe contenant project_id, user_query, et context

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    logger.info("Refining existing backlog with new directive...")

    # Récupérer la directive utilisateur (requête reformulée)
    directive = state.get("rewritten_task", "") or state.get("user_query", "")

    if not directive:
        logger.warning("No directive found in state")
        return {
            "status": "error",
            "result": "No directive provided for backlog refinement",
        }

    logger.info(f"Directive: {directive}")

    # Récupérer le thread_id et la queue d'événements
    thread_id = state.get("thread_id", "")
    event_queue = get_event_queue(thread_id) if thread_id else None

    # Initialiser la liste d'événements
    agent_events = []

    # Émettre l'événement AgentStart
    start_event = {
        "type": "agent_start",
        "thought": f"Je vais raffiner le backlog existant en tenant compte de cette nouvelle précision : « {directive} ». Mon objectif est de privilégier la modification des items existants plutôt que de tout recréer.",
        "agent_name": "RefinerAgent",
    }
    agent_events.append(start_event)
    if event_queue:
        event_queue.put(start_event)

    # Émettre le plan d'action
    plan_event = {
        "type": "agent_plan",
        "steps": [
            "Chargement du backlog existant du projet",
            "Analyse de la directive de raffinement",
            "Évaluation de l'impact sur chaque work item",
            "Construction de l'ImpactPlan (modifications, suppressions, créations)",
        ],
        "agent_name": "RefinerAgent",
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
        "tool_name": "Chargement du backlog",
        "tool_icon": "📚",
        "description": "Chargement du backlog existant à raffiner",
        "status": "running",
        "details": {},
    }
    agent_events.append(load_event)
    if event_queue:
        event_queue.put(load_event)

    try:
        existing_items = storage.load_context(project_id)
        logger.info(f"Loaded {len(existing_items)} existing work items")

        if len(existing_items) == 0:
            logger.warning("No existing backlog found to refine")
            load_event_error = {
                "type": "tool_used",
                "tool_run_id": load_run_id,
                "tool_name": "Chargement du backlog",
                "tool_icon": "📚",
                "description": "Chargement du backlog existant à raffiner",
                "status": "error",
                "details": {"error": "Aucun backlog existant à raffiner"},
            }
            agent_events[-1] = load_event_error
            if event_queue:
                event_queue.put(load_event_error)
            return {
                "status": "error",
                "result": "Aucun backlog existant à raffiner. Veuillez d'abord créer un backlog.",
                "agent_events": agent_events,
            }

        load_event_completed = {
            "type": "tool_used",
            "tool_run_id": load_run_id,
            "tool_name": "Chargement du backlog",
            "tool_icon": "📚",
            "description": "Chargement du backlog existant à raffiner",
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
            "tool_name": "Chargement du backlog",
            "tool_icon": "📚",
            "description": "Chargement du backlog existant à raffiner",
            "status": "error",
            "details": {"error": f"No backlog found for project {project_id}"},
        }
        agent_events[-1] = load_event_error
        if event_queue:
            event_queue.put(load_event_error)
        return {
            "status": "error",
            "result": f"Aucun backlog existant trouvé pour le projet {project_id}",
            "agent_events": agent_events,
        }

    # Préparer la liste des work items pour le LLM (format JSON simplifié)
    work_items_for_llm = []
    for item in existing_items:
        work_items_for_llm.append({
            "id": item.id,
            "type": item.type,
            "title": item.title,
            "description": item.description or "",
            "parent_id": item.parent_id,
        })

    work_items_json = json.dumps(work_items_for_llm, ensure_ascii=False, indent=2)

    # Charger le prompt
    prompt_config = load_refine_backlog_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].format(
        directive=directive,
        work_items_json=work_items_json,
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
        "tool_name": "Analyse de raffinement",
        "tool_icon": "🧠",
        "description": f"Analyse de l'impact de la directive sur le backlog avec {model}",
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
        logger.debug(f"Raw LLM response:\n{response_text}")

        # Mettre à jour le statut
        llm_event_completed = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Analyse de raffinement",
            "tool_icon": "🧠",
            "description": f"Analyse de l'impact de la directive sur le backlog avec {model}",
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

        # Parser la réponse JSON de manière robuste
        refinement_plan = extract_and_parse_json(response_text)

        if not isinstance(refinement_plan, dict):
            raise ValueError("LLM response is not a valid refinement plan (expected dict)")

        # Extraire les listes de modifications, suppressions et créations
        modifications = refinement_plan.get("modifications", [])
        deletions = refinement_plan.get("deletions", [])
        creations = refinement_plan.get("creations", [])

        logger.info(f"Refinement plan: {len(modifications)} modifications, "
                    f"{len(deletions)} deletions, {len(creations)} creations")

        # Construire l'ImpactPlan
        # 1. Gérer les modifications
        modified_items = []
        for modification in modifications:
            item_id = modification.get("id")
            new_title = modification.get("title")
            new_description = modification.get("description")

            if not item_id or not new_title or not new_description:
                logger.warning(f"Invalid modification entry: {modification}")
                continue

            # Trouver l'item original
            original_item = None
            for item in existing_items:
                if item.id == item_id:
                    original_item = item
                    break

            if not original_item:
                logger.warning(f"Item {item_id} not found in backlog, skipping modification")
                continue

            # Créer l'état "before"
            item_before = original_item.model_copy(deep=True)

            # Créer l'état "after" avec les nouvelles valeurs
            item_after = original_item.model_copy(deep=True)
            item_after.title = new_title
            item_after.description = new_description

            # Gérer le statut de validation
            if item_before.validation_status == "human_validated":
                item_after.validation_status = "ia_modified"

            modified_items.append({
                "before": item_before.model_dump(),
                "after": item_after.model_dump(),
            })

            logger.info(f"  Modified: {item_id} - {new_title}")

        # 2. Gérer les suppressions
        deleted_items = []
        for item_id in deletions:
            # Vérifier que l'item existe
            item_exists = any(item.id == item_id for item in existing_items)
            if item_exists:
                deleted_items.append(item_id)
                logger.info(f"  Deleted: {item_id}")
            else:
                logger.warning(f"Item {item_id} not found for deletion, skipping")

        # 3. Gérer les créations
        new_items = []
        for creation_data in creations:
            # Ajouter le project_id
            creation_data["project_id"] = project_id

            # Générer un ID temporaire si absent
            if "id" not in creation_data:
                creation_data["id"] = f"temp-{uuid.uuid4().hex[:8]}"

            # Créer le WorkItem
            work_item = WorkItem(**creation_data)
            new_items.append(work_item.model_dump())

            logger.info(f"  Created: {work_item.type} - {work_item.title}")

        # Construire l'ImpactPlan final
        impact_plan = {
            "new_items": new_items,
            "modified_items": modified_items,
            "deleted_items": deleted_items,
        }

        logger.info("ImpactPlan created successfully")
        logger.info(f"- {len(new_items)} new items")
        logger.info(f"- {len(modified_items)} modified items")
        logger.info(f"- {len(deleted_items)} deleted items")
        logger.info("Workflow paused, awaiting human approval")

        # Émettre l'événement de construction de l'ImpactPlan
        plan_build_run_id = str(uuid.uuid4())
        plan_build_event = {
            "type": "tool_used",
            "tool_run_id": plan_build_run_id,
            "tool_name": "Construction ImpactPlan",
            "tool_icon": "📋",
            "description": "Création du plan d'impact avec les raffinements proposés",
            "status": "completed",
            "details": {
                "new_items_count": len(new_items),
                "modified_items_count": len(modified_items),
                "deleted_items_count": len(deleted_items),
            },
        }
        agent_events.append(plan_build_event)
        if event_queue:
            event_queue.put(plan_build_event)

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Backlog raffiné : {len(modified_items)} modifications, "
                     f"{len(deletions)} suppressions, {len(new_items)} créations",
            "agent_events": agent_events,
        }

    except JSONParsingError as e:
        logger.error(f"Failed to parse LLM response after extraction: {e}", exc_info=True)
        llm_event_error = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Analyse de raffinement",
            "tool_icon": "🧠",
            "description": f"Analyse de l'impact de la directive sur le backlog avec {model}",
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
        logger.error("Error during backlog refinement.", exc_info=True)
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
            "result": f"Failed to refine backlog: {e}",
            "agent_events": agent_events,
        }
