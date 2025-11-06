"""LangGraph workflow orchestrator for Agent4BA."""

import json
import os
from pathlib import Path
from typing import Any, Literal, TypedDict

import yaml
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from litellm import completion

from agent4ba.ai import backlog_agent

# Charger les variables d'environnement
load_dotenv()


class GraphState(TypedDict):
    """État partagé dans le graphe LangGraph."""

    project_id: str
    user_query: str
    intent: dict[str, Any]
    next_node: str
    agent_task: str
    impact_plan: dict[str, Any]
    status: str
    result: str


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

        return {"intent": intent}

    except json.JSONDecodeError as e:
        print(f"[INTENT_CLASSIFIER_NODE] Error parsing JSON: {e}")
        # Fallback: intention inconnue
        return {
            "intent": {
                "intent_id": "unknown",
                "confidence": 0.0,
                "args": {},
            }
        }
    except Exception as e:
        print(f"[INTENT_CLASSIFIER_NODE] Error calling LLM: {e}")
        # Fallback: intention inconnue
        return {
            "intent": {
                "intent_id": "unknown",
                "confidence": 0.0,
                "args": {},
            }
        }


def router_node(state: GraphState) -> dict[str, Any]:
    """
    Route la requête vers le bon agent selon l'intention.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec next_node et agent_task
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
            "agent_task": "none",
            "result": f"Intent confidence too low ({confidence:.2f}). Please rephrase your query.",
        }

    # Mapping des intentions vers les tâches d'agent
    intent_to_task = {
        "generate_spec": "generate_specification",
        "extract_features_from_docs": "extract_features",
        "review_backlog_quality": "review_quality",
        "search_requirements": "search_requirements",
        "decompose_objective": "decompose_objective",
        "estimate_stories": "estimate_stories",
        "improve_item_description": "improve_description",
    }

    agent_task = intent_to_task.get(intent_id, "unknown_task")

    if agent_task == "unknown_task":
        print(f"[ROUTER_NODE] Unknown intent '{intent_id}', routing to end")
        return {
            "next_node": "end",
            "agent_task": "none",
            "result": f"Intent '{intent_id}' is not recognized.",
        }

    print(f"[ROUTER_NODE] Selected agent task: {agent_task}")
    print("[ROUTER_NODE] Routing to agent node")

    return {
        "next_node": "agent",
        "agent_task": agent_task,
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

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec le résultat
    """
    agent_task = state.get("agent_task", "unknown_task")

    print("[AGENT_NODE] Routing to specific agent...")
    print(f"[AGENT_NODE] Agent task: {agent_task}")

    # Router vers le bon agent selon la tâche
    if agent_task == "decompose_objective":
        return backlog_agent.decompose_objective(state)

    # Stubs pour les autres agents (à implémenter)
    elif agent_task == "generate_specification":
        return {
            "status": "completed",
            "result": "Stub: Generating detailed specification (not yet implemented)",
        }

    elif agent_task == "extract_features":
        return {
            "status": "completed",
            "result": "Stub: Extracting features from documents (not yet implemented)",
        }

    elif agent_task == "review_quality":
        return {
            "status": "completed",
            "result": "Stub: Reviewing backlog quality (not yet implemented)",
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

    elif agent_task == "improve_description":
        return {
            "status": "completed",
            "result": "Stub: Improving work item description (not yet implemented)",
        }

    else:
        return {
            "status": "error",
            "result": f"Unknown agent task: {agent_task}",
        }


def approval_node(state: GraphState) -> dict[str, Any]:
    """
    Point d'interruption pour validation humaine.

    Ce nœud ne fait rien, mais le graphe s'interrompt avant son exécution
    grâce à interrupt_before=["approval"] lors de la compilation.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état
    """
    print("[APPROVAL_NODE] Human validation received, continuing workflow...")
    return {}


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

# Compilation du graphe avec interruption avant le nœud approval
# Cela permet d'attendre la validation humaine avant de continuer
app = workflow.compile(interrupt_before=["approval"])
