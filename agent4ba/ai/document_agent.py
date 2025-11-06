"""Document agent for extracting requirements from unstructured text."""

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


def load_extract_requirements_prompt() -> dict[str, Any]:
    """
    Charge le prompt d'extraction d'exigences depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "extract_requirements.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def extract_requirements(state: Any) -> dict[str, Any]:
    """
    Extrait les exigences d'un document texte non structuré et les transforme en work items.

    Args:
        state: État actuel du graphe contenant project_id et document_content

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    print("[DOCUMENT_AGENT] Extracting requirements from document...")

    # Récupérer le contenu du document depuis l'état
    document_content = state.get("document_content", "")

    if not document_content or not document_content.strip():
        print("[DOCUMENT_AGENT] No document content provided")
        return {
            "status": "error",
            "result": "No document content provided for requirement extraction",
        }

    print(f"[DOCUMENT_AGENT] Document length: {len(document_content)} characters")

    # Charger le contexte du projet
    project_id = state.get("project_id", "")
    storage = ProjectContextService()

    try:
        existing_items = storage.load_context(project_id)
        context_summary = f"Backlog actuel avec {len(existing_items)} work items"
        print(f"[DOCUMENT_AGENT] Loaded {len(existing_items)} existing work items")
    except FileNotFoundError:
        existing_items = []
        context_summary = "Nouveau projet sans backlog existant"
        print("[DOCUMENT_AGENT] No existing backlog found")

    # Charger le prompt
    prompt_config = load_extract_requirements_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].format(
        document_content=document_content,
        context=context_summary,
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    print(f"[DOCUMENT_AGENT] Using model: {model}")

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

        print(f"[DOCUMENT_AGENT] LLM response received: {len(response_text)} characters")

        # Parser la réponse JSON
        work_items_data = json.loads(response_text)

        if not isinstance(work_items_data, list):
            raise ValueError("LLM response is not a list of work items")

        print(f"[DOCUMENT_AGENT] Extracted {len(work_items_data)} work items")

        # Valider et convertir en WorkItem
        new_items = []
        for item_data in work_items_data:
            # Ajouter le project_id
            item_data["project_id"] = project_id

            # Créer le WorkItem (validation Pydantic)
            work_item = WorkItem(**item_data)
            new_items.append(work_item)

            print(f"[DOCUMENT_AGENT]   - {work_item.type}: {work_item.title}")

        # Construire l'ImpactPlan
        impact_plan = {
            "new_items": [item.model_dump() for item in new_items],
            "modified_items": [],
            "deleted_items": [],
        }

        print("[DOCUMENT_AGENT] ImpactPlan created successfully")
        print(f"[DOCUMENT_AGENT] - {len(new_items)} new items")
        print("[DOCUMENT_AGENT] Workflow paused, awaiting human approval")

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Extracted {len(new_items)} work items from document",
        }

    except json.JSONDecodeError as e:
        print(f"[DOCUMENT_AGENT] Error parsing JSON: {e}")
        return {
            "status": "error",
            "result": f"Failed to parse LLM response as JSON: {e}",
        }
    except Exception as e:
        print(f"[DOCUMENT_AGENT] Error: {e}")
        return {
            "status": "error",
            "result": f"Failed to extract requirements: {e}",
        }
