"""Schema architect agent for modifying project schemas."""

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
from agent4ba.core.storage import ProjectContextService
from agent4ba.models.schema import ProjectSchema
from agent4ba.utils.json_parser import JSONParsingError, extract_and_parse_json

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger = setup_logger(__name__)


def load_modify_schema_prompt() -> dict[str, Any]:
    """
    Charge le prompt de modification de schéma depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "modify_schema.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def modify_schema(state: Any) -> dict[str, Any]:
    """
    Modifie le schéma de projet en fonction de la demande utilisateur.

    Cette méthode analyse la demande de l'utilisateur et propose un nouveau
    schéma de projet complet incluant les modifications demandées.

    Args:
        state: État actuel du graphe contenant project_id et user_query

    Returns:
        Mise à jour de l'état avec le nouveau schéma et status
    """
    logger.info("Modifying project schema based on user request...")

    # Récupérer la demande utilisateur (requête reformulée ou originale)
    user_request = state.get("rewritten_task", "") or state.get("user_query", "")

    if not user_request:
        logger.warning("No user request found in state")
        return {
            "status": "error",
            "result": "No user request provided for schema modification",
        }

    logger.info(f"User request: {user_request}")

    # Récupérer le thread_id et la queue d'événements
    thread_id = state.get("thread_id", "")
    event_queue = get_event_queue(thread_id) if thread_id else None

    # Initialiser la liste d'événements
    agent_events = []

    # Émettre l'événement AgentStart
    start_event = {
        "type": "agent_start",
        "thought": f"Je vais analyser la demande « {user_request} » et modifier le schéma du projet en conséquence. Mon objectif est de générer un nouveau schéma ProjectSchema valide et complet.",
        "agent_name": "SchemaArchitectAgent",
    }
    agent_events.append(start_event)
    if event_queue:
        event_queue.put(start_event)

    # Émettre le plan d'action
    plan_event = {
        "type": "agent_plan",
        "steps": [
            "Chargement du schéma de projet actuel (project_schema.json)",
            "Analyse de la demande de modification",
            "Génération du nouveau schéma ProjectSchema complet",
            "Validation de la structure du nouveau schéma",
        ],
        "agent_name": "SchemaArchitectAgent",
    }
    agent_events.append(plan_event)
    if event_queue:
        event_queue.put(plan_event)

    # Charger le contexte du projet
    project_id = state.get("project_id", "")
    storage = ProjectContextService()

    # Émettre l'événement de chargement du schéma
    load_run_id = str(uuid.uuid4())
    load_event = {
        "type": "tool_used",
        "tool_run_id": load_run_id,
        "tool_name": "Chargement du schéma",
        "tool_icon": "📐",
        "description": "Chargement du schéma de projet actuel",
        "status": "running",
        "details": {},
    }
    agent_events.append(load_event)
    if event_queue:
        event_queue.put(load_event)

    try:
        # Charger le schéma actuel
        current_schema = storage.get_project_schema(project_id)
        logger.info(f"Loaded current schema with {len(current_schema.work_item_types)} work item types")

        load_event_completed = {
            "type": "tool_used",
            "tool_run_id": load_run_id,
            "tool_name": "Chargement du schéma",
            "tool_icon": "📐",
            "description": "Chargement du schéma de projet actuel",
            "status": "completed",
            "details": {"work_item_types_count": len(current_schema.work_item_types)},
        }
        agent_events[-1] = load_event_completed
        if event_queue:
            event_queue.put(load_event_completed)

    except FileNotFoundError:
        logger.error(f"Schema not found for project {project_id}")
        load_event_error = {
            "type": "tool_used",
            "tool_run_id": load_run_id,
            "tool_name": "Chargement du schéma",
            "tool_icon": "📐",
            "description": "Chargement du schéma de projet actuel",
            "status": "error",
            "details": {"error": f"Schema not found for project {project_id}"},
        }
        agent_events[-1] = load_event_error
        if event_queue:
            event_queue.put(load_event_error)
        return {
            "status": "error",
            "result": f"Schéma introuvable pour le projet {project_id}",
            "agent_events": agent_events,
        }

    # Convertir le schéma en JSON pour le LLM
    current_schema_json = json.dumps(
        current_schema.model_dump(),
        ensure_ascii=False,
        indent=2
    )

    # Charger le prompt
    prompt_config = load_modify_schema_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].format(
        user_request=user_request,
        current_schema_json=current_schema_json,
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
        "tool_name": "Génération du nouveau schéma",
        "tool_icon": "🧠",
        "description": f"Génération du nouveau schéma avec {model}",
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
            "tool_name": "Génération du nouveau schéma",
            "tool_icon": "🧠",
            "description": f"Génération du nouveau schéma avec {model}",
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
        new_schema_dict = extract_and_parse_json(response_text)

        if not isinstance(new_schema_dict, dict):
            raise ValueError("LLM response is not a valid schema (expected dict)")

        # Valider et créer le nouveau ProjectSchema
        new_schema = ProjectSchema(**new_schema_dict)

        logger.info(f"New schema generated successfully with {len(new_schema.work_item_types)} work item types")

        # LOG CRUCIAL: Afficher le nouveau schéma généré
        logger.info("[SCHEMA_ARCHITECT] New schema generated:")
        logger.info(f"\n{json.dumps(new_schema.model_dump(), ensure_ascii=False, indent=2)}")

        # Émettre l'événement de validation du schéma
        validation_run_id = str(uuid.uuid4())
        validation_event = {
            "type": "tool_used",
            "tool_run_id": validation_run_id,
            "tool_name": "Validation du schéma",
            "tool_icon": "✅",
            "description": "Validation de la structure du nouveau schéma",
            "status": "completed",
            "details": {
                "work_item_types_count": len(new_schema.work_item_types),
                "valid": True,
            },
        }
        agent_events.append(validation_event)
        if event_queue:
            event_queue.put(validation_event)

        # Retourner le nouveau schéma dans l'état
        return {
            "new_schema": new_schema.model_dump(),
            "status": "completed",
            "result": f"Nouveau schéma généré avec succès : {len(new_schema.work_item_types)} types de work items définis",
            "agent_events": agent_events,
        }

    except JSONParsingError as e:
        logger.error(f"Failed to parse LLM response after extraction: {e}", exc_info=True)
        llm_event_error = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Génération du nouveau schéma",
            "tool_icon": "🧠",
            "description": f"Génération du nouveau schéma avec {model}",
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
        logger.error("Error during schema modification.", exc_info=True)
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
            "result": f"Failed to modify schema: {e}",
            "agent_events": agent_events,
        }
