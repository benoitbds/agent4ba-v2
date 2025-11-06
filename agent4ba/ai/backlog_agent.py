"""Backlog agent for managing project backlogs with AI assistance."""

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from litellm import completion

from agent4ba.core.models import WorkItem
from agent4ba.core.storage import ProjectContextService

# Charger les variables d'environnement
load_dotenv()


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


def decompose_objective(state: Any) -> dict[str, Any]:
    """
    Décompose un objectif métier en work items structurés.

    Args:
        state: État actuel du graphe contenant project_id, intent avec objective

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    print("[BACKLOG_AGENT] Decomposing objective into work items...")

    # Récupérer l'objectif depuis l'intention
    intent = state.get("intent", {})
    objective = intent.get("args", {}).get("objective", "")

    if not objective:
        print("[BACKLOG_AGENT] No objective found in intent args")
        return {
            "status": "error",
            "result": "No objective provided for decomposition",
        }

    print(f"[BACKLOG_AGENT] Objective: {objective}")

    # Charger le contexte du projet
    project_id = state.get("project_id", "")
    storage = ProjectContextService()

    try:
        existing_items = storage.load_context(project_id)
        context_summary = f"Backlog actuel avec {len(existing_items)} work items"
        print(f"[BACKLOG_AGENT] Loaded {len(existing_items)} existing work items")
    except FileNotFoundError:
        existing_items = []
        context_summary = "Nouveau projet sans backlog existant"
        print("[BACKLOG_AGENT] No existing backlog found")

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

    print(f"[BACKLOG_AGENT] Using model: {model}")

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

        print(f"[BACKLOG_AGENT] LLM response received: {len(response_text)} characters")

        # Parser la réponse JSON
        work_items_data = json.loads(response_text)

        if not isinstance(work_items_data, list):
            raise ValueError("LLM response is not a list of work items")

        print(f"[BACKLOG_AGENT] Generated {len(work_items_data)} work items")

        # Valider et convertir en WorkItem
        new_items = []
        for item_data in work_items_data:
            # Ajouter le project_id
            item_data["project_id"] = project_id

            # Créer le WorkItem (validation Pydantic)
            work_item = WorkItem(**item_data)
            new_items.append(work_item)

            print(f"[BACKLOG_AGENT]   - {work_item.type}: {work_item.title}")

        # Construire l'ImpactPlan
        impact_plan = {
            "new_items": [item.model_dump() for item in new_items],
            "modified_items": [],
            "deleted_items": [],
        }

        print("[BACKLOG_AGENT] ImpactPlan created successfully")
        print(f"[BACKLOG_AGENT] - {len(new_items)} new items")
        print("[BACKLOG_AGENT] Workflow paused, awaiting human approval")

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Generated {len(new_items)} work items for objective: {objective}",
        }

    except json.JSONDecodeError as e:
        print(f"[BACKLOG_AGENT] Error parsing JSON: {e}")
        return {
            "status": "error",
            "result": f"Failed to parse LLM response as JSON: {e}",
        }
    except Exception as e:
        print(f"[BACKLOG_AGENT] Error: {e}")
        return {
            "status": "error",
            "result": f"Failed to decompose objective: {e}",
        }
