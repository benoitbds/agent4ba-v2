"""LangGraph workflow orchestrator for Agent4BA."""

import json
import os
from pathlib import Path
from typing import Any, Literal, TypedDict

import yaml
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from litellm import completion

from agent4ba.ai import backlog_agent, document_agent
from agent4ba.core.registry_service import load_agent_registry
from agent4ba.core.storage import ProjectContextService

# Charger les variables d'environnement
load_dotenv()

# Charger la configuration des agents et des intentions
print("[GRAPH] Loading agent registry configuration...")
_AGENT_REGISTRY = load_agent_registry()
print(f"[GRAPH] Loaded {len(_AGENT_REGISTRY.agents)} agents and "
      f"{len(_AGENT_REGISTRY.intent_mapping)} intent mappings")

# Créer un dictionnaire de lookup pour accéder rapidement aux mappings d'intentions
INTENT_CONFIG_MAP = {
    mapping.intent_id: mapping
    for mapping in _AGENT_REGISTRY.intent_mapping
}


class GraphState(TypedDict):
    """État partagé dans le graphe LangGraph."""

    project_id: str
    user_query: str
    document_content: str
    intent: dict[str, Any]
    intent_args: dict[str, Any]  # Arguments extraits de l'intention
    next_node: str
    agent_id: str  # ID de l'agent à exécuter (ex: "backlog_agent")
    agent_task: str  # Tâche à exécuter par l'agent (ex: "decompose_objective")
    impact_plan: dict[str, Any]
    status: str
    approval_decision: bool | None
    result: str
    agent_events: list[dict[str, Any]]
    thread_id: str  # Ajout du thread_id pour accéder à la queue


def load_intent_classifier_prompt() -> dict[str, Any]:
    """
    Charge le prompt de classification depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "intent_classifier.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def entry_node(state: GraphState) -> dict[str, Any]:
    """
    Point d'entrée du graphe.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état
    """
    print(f"[ENTRY_NODE] Processing query for project: {state['project_id']}")
    print(f"[ENTRY_NODE] User query: {state['user_query']}")
    return {}


def intent_classifier_node(state: GraphState) -> dict[str, Any]:
    """
    Classifie l'intention de l'utilisateur avec un LLM.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec l'intention détectée
    """
    print("[INTENT_CLASSIFIER_NODE] Classifying user intent with LLM...")

    # Charger le prompt
    prompt_config = load_intent_classifier_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].format(
        user_query=state["user_query"]
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    print(f"[INTENT_CLASSIFIER_NODE] Using model: {model}")

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

        print(f"[INTENT_CLASSIFIER_NODE] LLM response: {response_text}")

        # Parser la réponse JSON
        intent = json.loads(response_text)

        print(f"[INTENT_CLASSIFIER_NODE] Detected intent: {intent['intent_id']}")
        print(f"[INTENT_CLASSIFIER_NODE] Confidence: {intent['confidence']}")
        print(f"[INTENT_CLASSIFIER_NODE] Args: {intent.get('args', {})}")

        return {
            "intent": intent,
            "intent_args": intent.get("args", {}),
        }

    except json.JSONDecodeError as e:
        print(f"[INTENT_CLASSIFIER_NODE] Error parsing JSON: {e}")
        # Fallback: intention inconnue
        return {
            "intent": {
                "intent_id": "unknown",
                "confidence": 0.0,
                "args": {},
            },
            "intent_args": {},
        }
    except Exception as e:
        print(f"[INTENT_CLASSIFIER_NODE] Error calling LLM: {e}")
        # Fallback: intention inconnue
        return {
            "intent": {
                "intent_id": "unknown",
                "confidence": 0.0,
                "args": {},
            },
            "intent_args": {},
        }


def router_node(state: GraphState) -> dict[str, Any]:
    """
    Route la requête vers le bon agent selon l'intention.

    Utilise la configuration chargée depuis agent_registry.yaml pour
    déterminer quel agent doit traiter quelle intention.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec next_node, agent_id et agent_task
    """
    intent = state.get("intent", {})
    intent_id = intent.get("intent_id", "unknown")
    confidence = intent.get("confidence", 0.0)

    print(f"[ROUTER_NODE] Routing based on intent: {intent_id}")
    print(f"[ROUTER_NODE] Confidence: {confidence}")

    # Seuil de confiance minimum
    confidence_threshold = 0.7

    if confidence < confidence_threshold:
        print(f"[ROUTER_NODE] Low confidence ({confidence}), routing to end")
        return {
            "next_node": "end",
            "agent_id": "none",
            "agent_task": "none",
            "result": f"Intent confidence too low ({confidence:.2f}). Please rephrase your query.",
        }

    # Rechercher la configuration de l'intention dans le registre
    intent_config = INTENT_CONFIG_MAP.get(intent_id)

    if intent_config is None:
        print(f"[ROUTER_NODE] Unknown intent '{intent_id}', routing to end")
        return {
            "next_node": "end",
            "agent_id": "none",
            "agent_task": "none",
            "result": f"Intent '{intent_id}' is not recognized.",
        }

    # Vérifier si l'intention est implémentée
    if intent_config.status == "not_implemented":
        print(f"[ROUTER_NODE] Intent '{intent_id}' is not yet implemented, routing to end")
        return {
            "next_node": "end",
            "agent_id": intent_config.agent_id,
            "agent_task": intent_config.agent_task,
            "result": f"Intent '{intent_id}' is not yet implemented.",
        }

    print(f"[ROUTER_NODE] Selected agent: {intent_config.agent_id}")
    print(f"[ROUTER_NODE] Selected task: {intent_config.agent_task}")
    print("[ROUTER_NODE] Routing to agent node")

    return {
        "next_node": "agent",
        "agent_id": intent_config.agent_id,
        "agent_task": intent_config.agent_task,
    }


def should_continue_to_agent(
    state: GraphState,
) -> Literal["agent", "end"]:
    """
    Fonction de routage conditionnel depuis le router.

    Args:
        state: État actuel du graphe

    Returns:
        Nom du prochain nœud
    """
    next_node = state.get("next_node", "end")
    return "agent" if next_node == "agent" else "end"


def should_continue_after_agent(
    state: GraphState,
) -> Literal["approval", "end"]:
    """
    Fonction de routage conditionnel après l'agent.

    Si le status est "awaiting_approval", on va vers le nœud approval
    qui déclenche une interruption pour validation humaine.

    Args:
        state: État actuel du graphe

    Returns:
        Nom du prochain nœud
    """
    status = state.get("status", "completed")
    if status == "awaiting_approval":
        return "approval"
    return "end"


def agent_node(state: GraphState) -> dict[str, Any]:
    """
    Exécute l'agent approprié pour traiter la requête.

    Dispatche vers le bon agent en se basant sur agent_id,
    puis exécute la tâche correspondant à agent_task.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec le résultat
    """
    agent_id = state.get("agent_id", "unknown")
    agent_task = state.get("agent_task", "unknown_task")

    print("[AGENT_NODE] Routing to specific agent...")
    print(f"[AGENT_NODE] Agent ID: {agent_id}")
    print(f"[AGENT_NODE] Agent task: {agent_task}")
    print(f"[AGENT_NODE_DEBUG] State received: {state}")

    # Dispatcher vers le bon agent selon agent_id
    if agent_id == "backlog_agent":
        print(f"[AGENT_NODE_DEBUG] Calling BacklogAgent method '{agent_task}'...")
        # Router vers la méthode appropriée du backlog_agent
        if agent_task == "decompose_objective":
            return backlog_agent.decompose_objective(state)
        elif agent_task == "review_quality":
            return backlog_agent.review_quality(state)
        elif agent_task == "improve_description":
            return backlog_agent.improve_description(state)
        elif agent_task == "generate_specification":
            return {
                "status": "completed",
                "result": "Stub: Generating detailed specification (not yet implemented)",
            }
        elif agent_task == "search_requirements":
            return {
                "status": "completed",
                "result": "Stub: Searching requirements (not yet implemented)",
            }
        elif agent_task == "estimate_stories":
            return {
                "status": "completed",
                "result": "Stub: Estimating story points (not yet implemented)",
            }
        else:
            return {
                "status": "error",
                "result": f"Unknown task '{agent_task}' for backlog_agent",
            }

    elif agent_id == "document_agent":
        print(f"[AGENT_NODE_DEBUG] Calling DocumentAgent method '{agent_task}'...")
        # Router vers la méthode appropriée du document_agent
        if agent_task == "extract_features":
            return document_agent.extract_requirements(state)
        else:
            return {
                "status": "error",
                "result": f"Unknown task '{agent_task}' for document_agent",
            }

    else:
        return {
            "status": "error",
            "result": f"Unknown agent: {agent_id}",
        }


def approval_node(state: GraphState) -> dict[str, Any]:
    """
    Traite l'approbation ou le rejet de l'ImpactPlan.

    Ce nœud est atteint après la reprise du workflow suite à une décision humaine.
    Il applique les changements de l'ImpactPlan si approuvé, sinon annule.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec le résultat final
    """
    print("[APPROVAL_NODE] Processing approval decision...")

    approval_decision = state.get("approval_decision")
    project_id = state.get("project_id", "")

    if approval_decision is None:
        print("[APPROVAL_NODE] No approval decision found, workflow interrupted")
        return {
            "status": "interrupted",
            "result": "Workflow interrupted, awaiting approval decision",
        }

    if not approval_decision:
        print("[APPROVAL_NODE] ImpactPlan rejected by user")
        return {
            "status": "rejected",
            "result": "ImpactPlan rejected. No changes were applied to the backlog.",
        }

    # L'utilisateur a approuvé, on applique l'ImpactPlan
    print("[APPROVAL_NODE] ImpactPlan approved by user, applying changes...")

    impact_plan = state.get("impact_plan", {})
    new_items = impact_plan.get("new_items", [])
    modified_items = impact_plan.get("modified_items", [])
    deleted_items = impact_plan.get("deleted_items", [])

    print(f"[APPROVAL_NODE] Changes to apply: {len(new_items)} new, "
          f"{len(modified_items)} modified, {len(deleted_items)} deleted")

    # Charger le backlog existant
    storage = ProjectContextService()

    try:
        existing_items = storage.load_context(project_id)
        print(f"[APPROVAL_NODE] Loaded {len(existing_items)} existing work items")
    except FileNotFoundError:
        existing_items = []
        print("[APPROVAL_NODE] No existing backlog found, starting fresh")

    from agent4ba.core.models import WorkItem

    # Convertir new_items en WorkItem si nécessaire
    new_work_items = []
    for item_data in new_items:
        if isinstance(item_data, dict):
            new_work_items.append(WorkItem(**item_data))
        else:
            new_work_items.append(item_data)

    # Gérer les modified_items (format: {"before": WorkItem, "after": WorkItem})
    modified_count = 0
    for modified_data in modified_items:
        if isinstance(modified_data, dict) and "after" in modified_data:
            # Extraire l'item "after"
            after_data = modified_data["after"]
            after_item = WorkItem(**after_data) if isinstance(after_data, dict) else after_data

            # Trouver et remplacer l'item correspondant dans existing_items
            for i, existing_item in enumerate(existing_items):
                if existing_item.id == after_item.id:
                    existing_items[i] = after_item
                    modified_count += 1
                    print(f"[APPROVAL_NODE] Updated item {after_item.id}")
                    break

    # Construire le nouveau backlog complet
    updated_backlog = existing_items + new_work_items

    print(f"[APPROVAL_NODE] New backlog size: {len(updated_backlog)} work items")

    # Sauvegarder le nouveau backlog (crée une nouvelle version)
    storage.save_backlog(project_id, updated_backlog)

    # Déterminer le numéro de version qui a été créé
    latest_version = storage._find_latest_backlog_version(project_id)

    print(f"[APPROVAL_NODE] Successfully saved backlog_v{latest_version}.json")

    result_parts = []
    if len(new_work_items) > 0:
        result_parts.append(f"Added {len(new_work_items)} new work items")
    if modified_count > 0:
        result_parts.append(f"Modified {modified_count} work items")

    result_message = "ImpactPlan approved and applied successfully. " + ". ".join(result_parts) + f". Backlog saved as version {latest_version}."

    return {
        "status": "approved",
        "result": result_message,
    }


def end_node(state: GraphState) -> dict[str, Any]:
    """
    Point de sortie du graphe.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état
    """
    print("[END_NODE] Workflow completed")
    print(f"[END_NODE] Final result: {state.get('result', 'No result')}")
    print(f"[END_NODE] Status: {state.get('status', 'unknown')}")
    return {}


# Construction du graphe
workflow = StateGraph(GraphState)

# Ajout des nœuds
workflow.add_node("entry", entry_node)
workflow.add_node("intent_classifier", intent_classifier_node)
workflow.add_node("router", router_node)
workflow.add_node("agent", agent_node)
workflow.add_node("approval", approval_node)
workflow.add_node("end", end_node)

# Définition des arêtes (flux)
workflow.set_entry_point("entry")
workflow.add_edge("entry", "intent_classifier")
workflow.add_edge("intent_classifier", "router")

# Routage conditionnel depuis le router
workflow.add_conditional_edges(
    "router",
    should_continue_to_agent,
    {
        "agent": "agent",
        "end": "end",
    },
)

# Routage conditionnel après l'agent
# Si status == "awaiting_approval", on va vers approval (avec interruption)
# Sinon, on va directement vers end
workflow.add_conditional_edges(
    "agent",
    should_continue_after_agent,
    {
        "approval": "approval",
        "end": "end",
    },
)

workflow.add_edge("approval", "end")
workflow.add_edge("end", END)

# Créer un checkpointer en mémoire pour gérer les états interrompus
# Cela permet de reprendre l'exécution après une interruption
checkpointer = MemorySaver()

# Compilation du graphe avec interruption avant le nœud approval
# Cela permet d'attendre la validation humaine avant de continuer
app = workflow.compile(checkpointer=checkpointer, interrupt_before=["approval"])
