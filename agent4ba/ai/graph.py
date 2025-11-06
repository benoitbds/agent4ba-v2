"""LangGraph workflow orchestrator for Agent4BA."""

import json
import os
from pathlib import Path
from typing import Any, Literal, TypedDict

import yaml
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from litellm import completion

# Charger les variables d'environnement
load_dotenv()


class GraphState(TypedDict):
    """État partagé dans le graphe LangGraph."""

    project_id: str
    user_query: str
    intent: dict[str, Any]
    next_node: str
    agent_task: str
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
    Fonction de routage conditionnel.

    Args:
        state: État actuel du graphe

    Returns:
        Nom du prochain nœud
    """
    next_node = state.get("next_node", "end")
    return "agent" if next_node == "agent" else "end"


def agent_node(state: GraphState) -> dict[str, Any]:
    """
    Exécute l'agent approprié pour traiter la requête.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec le résultat
    """
    agent_task = state.get("agent_task", "unknown_task")
    intent = state.get("intent", {})

    print("[AGENT_NODE] Executing agent logic...")
    print(f"[AGENT_NODE] Agent task: {agent_task}")
    print(f"[AGENT_NODE] Processing query: {state['user_query']}")
    print(f"[AGENT_NODE] Intent args: {intent.get('args', {})}")

    # Stub: génération d'un résultat basé sur la tâche
    task_descriptions = {
        "generate_specification": "Generating detailed specification",
        "extract_features": "Extracting features from documents",
        "review_quality": "Reviewing backlog quality",
        "search_requirements": "Searching requirements",
        "decompose_objective": "Decomposing objective into stories",
        "estimate_stories": "Estimating story points",
        "improve_description": "Improving work item description",
    }

    task_desc = task_descriptions.get(agent_task, "Processing request")
    result = f"{task_desc} for query: '{state['user_query']}' (project: {state['project_id']})"

    print(f"[AGENT_NODE] Generated result: {result}")
    return {"result": result}


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
    return {}


# Construction du graphe
workflow = StateGraph(GraphState)

# Ajout des nœuds
workflow.add_node("entry", entry_node)
workflow.add_node("intent_classifier", intent_classifier_node)
workflow.add_node("router", router_node)
workflow.add_node("agent", agent_node)
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

workflow.add_edge("agent", "end")
workflow.add_edge("end", END)

# Compilation du graphe
app = workflow.compile()
