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


def improve_description(state: Any) -> dict[str, Any]:
    """
    Améliore la description d'un work item existant.

    Args:
        state: État actuel du graphe contenant project_id, intent avec item_id

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    print("[BACKLOG_AGENT] Improving work item description...")

    # Récupérer l'item_id depuis l'intention
    intent = state.get("intent", {})
    item_id = intent.get("args", {}).get("item_id", "")

    if not item_id:
        print("[BACKLOG_AGENT] No item_id found in intent args")
        return {
            "status": "error",
            "result": "No item_id provided for description improvement",
        }

    print(f"[BACKLOG_AGENT] Item ID: {item_id}")

    # Charger le contexte du projet
    project_id = state.get("project_id", "")
    storage = ProjectContextService()

    try:
        existing_items = storage.load_context(project_id)
        print(f"[BACKLOG_AGENT] Loaded {len(existing_items)} existing work items")
    except FileNotFoundError:
        print("[BACKLOG_AGENT] No existing backlog found")
        return {
            "status": "error",
            "result": f"No backlog found for project {project_id}",
        }

    # Trouver l'item correspondant
    target_item = None
    for item in existing_items:
        if item.id == item_id:
            target_item = item
            break

    if target_item is None:
        print(f"[BACKLOG_AGENT] Item {item_id} not found in backlog")
        return {
            "status": "error",
            "result": f"Work item {item_id} not found in backlog",
        }

    print(f"[BACKLOG_AGENT] Found item: {target_item.type} - {target_item.title}")
    print(f"[BACKLOG_AGENT] Current description: {target_item.description}")

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
        improved_description = response.choices[0].message.content.strip()

        print(f"[BACKLOG_AGENT] LLM response received: {len(improved_description)} characters")
        print(f"[BACKLOG_AGENT] Improved description: {improved_description}")

        # Créer l'état "after" avec la nouvelle description
        item_after = target_item.model_copy(deep=True)
        item_after.description = improved_description

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

        print("[BACKLOG_AGENT] ImpactPlan created successfully")
        print("[BACKLOG_AGENT] - 1 modified item")
        print("[BACKLOG_AGENT] Workflow paused, awaiting human approval")

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Improved description for work item: {item_id}",
        }

    except Exception as e:
        print(f"[BACKLOG_AGENT] Error: {e}")
        return {
            "status": "error",
            "result": f"Failed to improve description: {e}",
        }


def review_quality(state: Any) -> dict[str, Any]:
    """
    Analyse la qualité des User Stories du backlog selon les critères INVEST.

    Args:
        state: État actuel du graphe contenant project_id

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    print("[BACKLOG_AGENT] Reviewing backlog quality with INVEST criteria...")

    # Charger le contexte du projet
    project_id = state.get("project_id", "")
    storage = ProjectContextService()

    try:
        existing_items = storage.load_context(project_id)
        print(f"[BACKLOG_AGENT] Loaded {len(existing_items)} existing work items")
    except FileNotFoundError:
        print("[BACKLOG_AGENT] No existing backlog found")
        return {
            "status": "error",
            "result": f"No backlog found for project {project_id}",
        }

    # Filtrer uniquement les stories (pas les features ni les tasks)
    stories = [item for item in existing_items if item.type == "story"]

    if len(stories) == 0:
        print("[BACKLOG_AGENT] No user stories found in backlog")
        return {
            "status": "completed",
            "result": "No user stories found in backlog to analyze",
        }

    print(f"[BACKLOG_AGENT] Found {len(stories)} user stories to analyze")

    # Charger le prompt
    prompt_config = load_invest_analysis_prompt()

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    print(f"[BACKLOG_AGENT] Using model: {model}")

    # Préparer le contexte du projet
    context_summary = f"Projet avec {len(existing_items)} work items dans le backlog ({len(stories)} user stories)"

    modified_items = []

    # Analyser chaque story
    for story in stories:
        print(f"[BACKLOG_AGENT] Analyzing story: {story.id} - {story.title}")

        # Sauvegarder l'état "before"
        item_before = story.model_copy(deep=True)

        # Préparer le prompt utilisateur
        user_prompt = prompt_config["user_prompt_template"].format(
            title=story.title,
            description=story.description or "",
            context=context_summary,
        )

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

            print(f"[BACKLOG_AGENT] LLM response received for {story.id}")

            # Parser la réponse JSON
            analysis_result = json.loads(response_text)

            if "invest_analysis" not in analysis_result:
                print(f"[BACKLOG_AGENT] Warning: No 'invest_analysis' in response for {story.id}")
                continue

            invest_analysis = analysis_result["invest_analysis"]

            print(f"[BACKLOG_AGENT] INVEST scores for {story.id}:")
            for criterion, data in invest_analysis.items():
                print(f"[BACKLOG_AGENT]   {criterion}: {data['score']:.2f} - {data['reason']}")

            # Créer l'état "after" avec l'analyse INVEST dans les attributes
            item_after = story.model_copy(deep=True)
            item_after.attributes["invest_analysis"] = invest_analysis

            # Ajouter à la liste des items modifiés
            modified_items.append({
                "before": item_before.model_dump(),
                "after": item_after.model_dump(),
            })

        except json.JSONDecodeError as e:
            print(f"[BACKLOG_AGENT] Error parsing JSON for {story.id}: {e}")
            continue
        except Exception as e:
            print(f"[BACKLOG_AGENT] Error analyzing {story.id}: {e}")
            continue

    if len(modified_items) == 0:
        print("[BACKLOG_AGENT] No stories were successfully analyzed")
        return {
            "status": "error",
            "result": "Failed to analyze any stories",
        }

    # Construire l'ImpactPlan avec modified_items
    impact_plan = {
        "new_items": [],
        "modified_items": modified_items,
        "deleted_items": [],
    }

    print("[BACKLOG_AGENT] ImpactPlan created successfully")
    print(f"[BACKLOG_AGENT] - {len(modified_items)} stories analyzed with INVEST criteria")
    print("[BACKLOG_AGENT] Workflow paused, awaiting human approval")

    return {
        "impact_plan": impact_plan,
        "status": "awaiting_approval",
        "result": f"Analyzed {len(modified_items)} user stories with INVEST criteria",
    }
