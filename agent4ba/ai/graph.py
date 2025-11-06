"""LangGraph workflow orchestrator for Agent4BA."""

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class GraphState(TypedDict):
    """État partagé dans le graphe LangGraph."""

    project_id: str
    user_query: str
    intent: dict[str, Any]
    result: str


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
    Classifie l'intention de l'utilisateur.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec l'intention détectée
    """
    print("[INTENT_CLASSIFIER_NODE] Classifying user intent...")

    # Stub: pour le moment, on retourne une intention factice
    intent = {
        "type": "query",
        "confidence": 0.95,
        "entities": [],
    }

    print(f"[INTENT_CLASSIFIER_NODE] Detected intent: {intent['type']}")
    return {"intent": intent}


def router_node(state: GraphState) -> dict[str, Any]:
    """
    Route la requête vers le bon agent selon l'intention.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état
    """
    intent_type = state.get("intent", {}).get("type", "unknown")
    print(f"[ROUTER_NODE] Routing based on intent: {intent_type}")
    print("[ROUTER_NODE] Selected agent: default_agent")
    return {}


def agent_node(state: GraphState) -> dict[str, Any]:
    """
    Exécute l'agent approprié pour traiter la requête.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec le résultat
    """
    print("[AGENT_NODE] Executing agent logic...")
    print(f"[AGENT_NODE] Processing query: {state['user_query']}")

    # Stub: génération d'un résultat factice
    result = f"Processed query '{state['user_query']}' for project {state['project_id']}"

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
workflow.add_edge("router", "agent")
workflow.add_edge("agent", "end")
workflow.add_edge("end", END)

# Compilation du graphe
app = workflow.compile()
