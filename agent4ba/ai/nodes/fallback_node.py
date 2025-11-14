"""Module pour gérer les requêtes hors-scope dans le workflow LangGraph."""

from typing import Any

from agent4ba.core.logger import setup_logger

# Configurer le logger
logger = setup_logger(__name__)


def handle_unknown_intent(state: dict[str, Any]) -> dict[str, Any]:
    """
    Nœud de fallback qui gère les requêtes non reconnues.

    Ce nœud est appelé lorsque le routeur détermine qu'aucune intention
    ne correspond à la requête utilisateur. Il ne fait aucun appel au LLM,
    mais retourne simplement un message d'erreur prédéfini pour orienter
    l'utilisateur vers les capacités réelles de l'agent.

    Args:
        state: État actuel du graphe contenant :
            - user_query: La requête originale de l'utilisateur
            - rewritten_task: La tâche reformulée
            - project_id: L'identifiant du projet

    Returns:
        dict: Mise à jour partielle de l'état avec :
            - result: Message d'erreur prédéfini
            - status: "completed" pour terminer proprement le workflow
    """
    logger.info("[FALLBACK_NODE] Handling unknown intent...")

    user_query = state.get("user_query", "")
    logger.info(f"[FALLBACK_NODE] User query: {user_query}")

    # Message de fallback prédéfini
    fallback_message = (
        "Désolé, je n'ai pas compris votre demande. Je suis spécialisé dans l'aide à la gestion de backlog. "
        "Voici ce que je peux faire pour vous :\n\n"
        "- Décomposer un objectif en work items (features, user stories)\n"
        "- Générer des critères d'acceptation pour une user story\n"
        "- Générer des cas de test pour un work item\n"
        "- Améliorer la description d'un work item\n"
        "- Faire une revue qualité du backlog\n"
        "- Extraire des fonctionnalités depuis un document\n\n"
        "Pouvez-vous reformuler votre demande en précisant l'une de ces actions ?"
    )

    logger.info(f"[FALLBACK_NODE] Returning fallback message")

    return {
        "result": fallback_message,
        "status": "completed",
    }
