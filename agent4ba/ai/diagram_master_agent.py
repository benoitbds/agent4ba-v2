"""Diagram Master Agent for generating Mermaid.js diagrams."""

import os
import uuid
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from litellm import completion

from agent4ba.api.event_queue import get_event_queue
from agent4ba.core.logger import setup_logger
from agent4ba.core.models import Diagram

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger = setup_logger(__name__)


def load_generate_diagram_prompt() -> dict[str, Any]:
    """
    Charge le prompt de génération de diagramme depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "generate_diagram.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def generate_diagram(state: Any) -> dict[str, Any]:
    """
    Génère un diagramme Mermaid.js à partir d'une description.

    Args:
        state: État actuel du graphe contenant project_id, rewritten_task, context

    Returns:
        Mise à jour de l'état avec le résultat (code Mermaid)
    """
    logger.info("[DiagramMasterAgent] Generating Mermaid diagram...")

    rewritten_task = state.get("rewritten_task", "")
    user_query = state.get("user_query", "")

    # Utiliser la requête reformulée si disponible, sinon la requête originale
    query = rewritten_task if rewritten_task else user_query

    logger.info(f"[DiagramMasterAgent] Query: {query}")

    # Récupérer le thread_id et la queue d'événements
    thread_id = state.get("thread_id", "")
    event_queue = get_event_queue(thread_id) if thread_id else None

    # Initialiser la liste d'événements
    agent_events = []

    # Émettre l'événement AgentStart
    start_event = {
        "type": "agent_start",
        "thought": "Je vais générer un diagramme Mermaid.js basé sur votre demande et le contexte fourni.",
        "agent_name": "DiagramMasterAgent",
    }
    agent_events.append(start_event)
    if event_queue:
        event_queue.put(start_event)

    # Émettre le plan d'action
    plan_event = {
        "type": "agent_plan",
        "steps": [
            "Analyse de la demande utilisateur",
            "Récupération du contexte (documents RAG)",
            "Génération du diagramme Mermaid via LLM",
            "Validation du format de sortie",
        ],
        "agent_name": "DiagramMasterAgent",
    }
    agent_events.append(plan_event)
    if event_queue:
        event_queue.put(plan_event)

    # Construire le contexte en priorité depuis le work item complet
    context_work_item = state.get("context_work_item")
    context = state.get("context", [])
    context_text = ""

    # Émettre l'événement de récupération du contexte
    context_run_id = str(uuid.uuid4())
    context_event = {
        "type": "tool_used",
        "tool_run_id": context_run_id,
        "tool_name": "Récupération contexte",
        "tool_icon": "📚",
        "description": "Chargement du work item ou des documents pour comprendre le processus",
        "status": "running",
        "details": {},
    }
    agent_events.append(context_event)
    if event_queue:
        event_queue.put(context_event)

    # Priorité 1: Utiliser le work item complet s'il est disponible
    if context_work_item:
        logger.info(f"[DiagramMasterAgent] Using full work item: {context_work_item.id}")
        context_parts = []

        # Ajouter le titre
        context_parts.append(f"# {context_work_item.title}")

        # Ajouter la description si présente
        if context_work_item.description:
            context_parts.append(f"## Description\n{context_work_item.description}")

        # Ajouter les critères d'acceptation si présents
        if context_work_item.acceptance_criteria and len(context_work_item.acceptance_criteria) > 0:
            criteria_text = "\n".join([f"- {criterion}" for criterion in context_work_item.acceptance_criteria])
            context_parts.append(f"## Critères d'acceptation\n{criteria_text}")

        context_text = "\n\n".join(context_parts)
        logger.info(f"[DiagramMasterAgent] Work item context loaded: {len(context_text)} chars")

        context_event_completed = {
            "type": "tool_used",
            "tool_run_id": context_run_id,
            "tool_name": "Récupération contexte",
            "tool_icon": "📚",
            "description": f"Work item '{context_work_item.id}' chargé avec succès",
            "status": "completed",
            "details": {
                "source": "work_item",
                "work_item_id": context_work_item.id,
                "chars_count": len(context_text)
            },
        }
        agent_events[-1] = context_event_completed
        if event_queue:
            event_queue.put(context_event_completed)

    # Priorité 2: Sinon, utiliser les chunks de documents RAG
    elif context and len(context) > 0:
        # Construire le texte de contexte à partir des chunks
        context_parts = []
        for ctx_item in context:
            ctx_type = ctx_item.get("type", "unknown")
            if ctx_type == "document":
                # Extraire le contenu du document/chunk
                content = ctx_item.get("content", "")
                name = ctx_item.get("name", "Document")
                context_parts.append(f"[{name}]:\n{content}")
            elif ctx_type == "work_item":
                # Si c'est un work item dans le contexte (sans être chargé complètement)
                description = ctx_item.get("description", "")
                name = ctx_item.get("name", ctx_item.get("id", "Work Item"))
                context_parts.append(f"[{name}]:\n{description}")

        context_text = "\n\n".join(context_parts)
        logger.info(f"[DiagramMasterAgent] RAG context loaded: {len(context)} items, {len(context_text)} chars")

        context_event_completed = {
            "type": "tool_used",
            "tool_run_id": context_run_id,
            "tool_name": "Récupération contexte",
            "tool_icon": "📚",
            "description": "Chunks de documents RAG chargés",
            "status": "completed",
            "details": {"source": "rag_documents", "items_count": len(context), "chars_count": len(context_text)},
        }
        agent_events[-1] = context_event_completed
        if event_queue:
            event_queue.put(context_event_completed)
    else:
        logger.warning("[DiagramMasterAgent] No context provided")
        context_event_completed = {
            "type": "tool_used",
            "tool_run_id": context_run_id,
            "tool_name": "Récupération contexte",
            "tool_icon": "📚",
            "description": "Aucun contexte fourni",
            "status": "completed",
            "details": {"source": "none", "items_count": 0, "warning": "Aucun contexte fourni"},
        }
        agent_events[-1] = context_event_completed
        if event_queue:
            event_queue.put(context_event_completed)

    # Charger le prompt
    prompt_config = load_generate_diagram_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].format(
        user_query=query,
        context=context_text if context_text else "Aucun contexte disponible",
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    logger.info(f"[DiagramMasterAgent] Using model: {model}")

    # Émettre l'événement d'appel LLM
    llm_run_id = str(uuid.uuid4())
    llm_event = {
        "type": "tool_used",
        "tool_run_id": llm_run_id,
        "tool_name": "Génération diagramme",
        "tool_icon": "🧠",
        "description": f"Création du diagramme Mermaid avec {model}",
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

        # Extraire la réponse (code Mermaid)
        mermaid_code = response.choices[0].message.content.strip()

        logger.info(f"[DiagramMasterAgent] Diagram generated: {len(mermaid_code)} characters")

        # Mettre à jour le statut de l'événement
        llm_event_completed = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Génération diagramme",
            "tool_icon": "🧠",
            "description": f"Création du diagramme Mermaid avec {model}",
            "status": "completed",
            "details": {
                "model": model,
                "temperature": temperature,
                "chars_count": len(mermaid_code),
            },
        }
        agent_events[-1] = llm_event_completed
        if event_queue:
            event_queue.put(llm_event_completed)

        # Déduire un titre pour le diagramme à partir de la requête
        diagram_title = query[:50] if len(query) <= 50 else query[:47] + "..."

        # Créer l'objet Diagram
        new_diagram = Diagram(title=diagram_title, code=mermaid_code)
        logger.info(f"[DiagramMasterAgent] Created diagram object with ID: {new_diagram.id}")

        # Construire l'ImpactPlan
        impact_plan = {}
        project_id = state.get("project_id", "")

        if context_work_item:
            # Si un work item de contexte existe, on propose de le modifier
            logger.info(f"[DiagramMasterAgent] Adding diagram to existing work item: {context_work_item.id}")

            # Créer l'état "before"
            item_before = context_work_item.model_copy(deep=True)

            # Créer l'état "after" avec le nouveau diagramme ajouté
            item_after = context_work_item.model_copy(deep=True)
            item_after.diagrams.append(new_diagram)

            # Si l'item était validé par un humain, le marquer comme modifié par l'IA
            if item_before.validation_status == "human_validated":
                item_after.validation_status = "ia_modified"

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

            logger.info("[DiagramMasterAgent] ImpactPlan created to modify existing work item")

        else:
            # Si aucun work item de contexte n'est fourni, créer un nouveau work item de type diagram
            logger.info("[DiagramMasterAgent] No context work item, creating new diagram work item")

            # Générer un ID temporaire pour le nouveau work item
            temp_id = f"{project_id}-DIAG-{uuid.uuid4().hex[:6]}"

            new_work_item = {
                "id": temp_id,
                "project_id": project_id,
                "type": "task",  # Temporairement de type task en attendant le support du type diagram
                "title": f"Diagramme: {diagram_title}",
                "description": f"Diagramme généré automatiquement:\n\n```mermaid\n{mermaid_code}\n```",
                "diagrams": [new_diagram.model_dump()],
                "validation_status": "ia_generated",
                "attributes": {"category": "diagram"},
            }

            impact_plan = {
                "new_items": [new_work_item],
                "modified_items": [],
                "deleted_items": [],
            }

            logger.info("[DiagramMasterAgent] ImpactPlan created to add new diagram work item")

        # Émettre l'événement de construction de l'ImpactPlan
        plan_build_run_id = str(uuid.uuid4())
        plan_build_event = {
            "type": "tool_used",
            "tool_run_id": plan_build_run_id,
            "tool_name": "Construction ImpactPlan",
            "tool_icon": "📋",
            "description": "Création du plan d'impact avec le diagramme généré",
            "status": "completed",
            "details": {
                "diagram_id": new_diagram.id,
                "has_context_item": context_work_item is not None,
            },
        }
        agent_events.append(plan_build_event)
        if event_queue:
            event_queue.put(plan_build_event)

        logger.info("[DiagramMasterAgent] Workflow paused, awaiting human approval")

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Generated diagram '{diagram_title}' with {len(mermaid_code)} characters of Mermaid code",
            "agent_events": agent_events,
        }

    except Exception as e:
        logger.error("[DiagramMasterAgent] Error during diagram generation.", exc_info=True)
        llm_event_error = {
            "type": "tool_used",
            "tool_run_id": llm_run_id,
            "tool_name": "Génération diagramme",
            "tool_icon": "🧠",
            "description": f"Création du diagramme Mermaid avec {model}",
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
            "result": f"Erreur lors de la génération du diagramme: {e}",
            "agent_events": agent_events,
        }
