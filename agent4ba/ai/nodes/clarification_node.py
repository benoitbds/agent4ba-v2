"""Module pour gérer la boucle de clarification dans le workflow LangGraph."""

from typing import Any

from agent4ba.core.logger import setup_logger

# Configurer le logger
logger = setup_logger(__name__)


def ask_for_clarification(state: dict[str, Any]) -> dict[str, Any]:
    """
    Nœud de clarification qui prépare une question pour l'utilisateur.

    Ce nœud est appelé lorsqu'une ambiguïté est détectée dans la requête utilisateur.
    Il analyse le contexte pour identifier les éléments ambigus et formule une question
    de clarification appropriée.

    Args:
        state: État actuel du graphe contenant :
            - user_query: La requête originale de l'utilisateur
            - context: Liste des items du projet (work items, documents, etc.)
            - rewritten_task: La tâche reformulée
            - ambiguous_intent: Flag indiquant qu'une ambiguïté a été détectée
            - clarification_question: Question déjà formulée par le routeur (optionnelle)

    Returns:
        dict: Mise à jour partielle de l'état avec :
            - clarification_needed: True pour indiquer qu'une clarification est nécessaire
            - clarification_question: La question à poser à l'utilisateur
            - status: "clarification_needed" pour mettre en pause le workflow
    """
    logger.info("[CLARIFICATION_NODE] Ambiguity detected, preparing clarification question...")

    user_query = state.get("user_query", "")
    context = state.get("context", [])
    rewritten_task = state.get("rewritten_task", "")
    existing_question = state.get("clarification_question", "")

    logger.info(f"[CLARIFICATION_NODE] User query: {user_query}")
    logger.info(f"[CLARIFICATION_NODE] Context items: {len(context) if context else 0}")

    # Si une question a déjà été formulée par le routeur, l'utiliser
    if existing_question:
        logger.info(f"[CLARIFICATION_NODE] Using existing question from router: {existing_question}")
        question = existing_question
    else:
        # Sinon, analyser le contexte pour identifier les éléments pertinents
        # Pour le MVP, on simule la détection en cherchant plusieurs items du même type
        relevant_items = []

        if context and len(context) > 0:
            # Filtrer les work items pertinents
            work_items = [item for item in context if item.get("type") == "work_item"]

            if len(work_items) > 1:
                relevant_items = work_items
                logger.info(f"[CLARIFICATION_NODE] Found {len(work_items)} work items in context")

        # Formuler la question de clarification
        if relevant_items:
            # Créer une liste des items avec leurs IDs et noms
            items_list = []
            for idx, item in enumerate(relevant_items, 1):
                item_id = item.get("id", "unknown")
                item_name = item.get("name", "Sans nom")
                items_list.append(f"{idx}. {item_id} - {item_name}")

            items_str = "\n".join(items_list)

            question = (
                f"J'ai détecté plusieurs items correspondant à votre requête '{user_query}'. "
                f"Pour quel item souhaitez-vous continuer ?\n\n{items_str}\n\n"
                f"Veuillez préciser le numéro ou l'ID de l'item."
            )
        else:
            # Cas général si aucun contexte spécifique n'est détecté
            question = (
                f"Votre requête '{user_query}' nécessite des précisions. "
                f"Pourriez-vous indiquer l'identifiant du work item concerné ? (ex: FIR-3, US-001)"
            )

    logger.info(f"[CLARIFICATION_NODE] Question: {question}")

    return {
        "clarification_needed": True,
        "clarification_question": question,
        "status": "clarification_needed",
        "next_node": "end",  # Pour ce MVP, on s'arrête après la clarification
    }
