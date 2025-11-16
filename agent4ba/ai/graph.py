"""LangGraph workflow orchestrator for Agent4BA."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Literal, TypedDict

import yaml
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from litellm import completion

from agent4ba.ai import (
    backlog_agent,
    diagram_master_agent,
    document_agent,
    epic_architect_agent,
    story_teller_agent,
    test_agent,
)
from agent4ba.ai.nodes import ask_for_clarification, handle_unknown_intent
from agent4ba.ai.schemas import RouterDecision
from agent4ba.api.timeline_service import TimelineEvent, get_timeline_service
from agent4ba.core.logger import setup_logger
from agent4ba.core.registry_service import load_agent_registry
from agent4ba.core.storage import ProjectContextService

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger = setup_logger(__name__)

# Charger la configuration des agents et des intentions
logger.info("Loading agent registry configuration...")
_AGENT_REGISTRY = load_agent_registry()
logger.info(f"Loaded {len(_AGENT_REGISTRY.agents)} agents and "
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
    context: list[dict] | None  # Contexte optionnel (documents ou work items ciblés)
    context_work_item: Any  # Work item complet chargé depuis le contexte (si présent)
    rewritten_task: str  # Tâche reformulée par le task_rewriter_node
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

    # Champs pour la boucle de clarification
    ambiguous_intent: bool  # Indique si une ambiguïté a été détectée
    clarification_needed: bool  # Indique si une clarification est nécessaire
    clarification_question: str | None  # Question à poser à l'utilisateur
    user_response: str | None  # Réponse de l'utilisateur à la question



def load_task_rewriter_prompt() -> dict[str, Any]:
    """
    Charge le prompt de reformulation de tâche depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "task_rewriter.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def load_router_prompt() -> dict[str, Any]:
    """
    Charge le prompt de routage depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "router.yaml"
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
    # LOG DEBUG 3/3: Afficher l'état complet reçu par le premier nœud
    logger.debug(f"[DEBUG] Entry node received state: {state}")

    logger.info(f"[ENTRY_NODE] Processing query for project: {state['project_id']}")
    logger.info(f"[ENTRY_NODE] User query: {state['user_query']}")

    # Logger le contexte si présent
    context = state.get("context")
    context_work_item = None

    if context:
        logger.info(f"[ENTRY_NODE] Context provided: {len(context)} items")
        for ctx_item in context:
            logger.info(f"[ENTRY_NODE]   - {ctx_item['type']}: {ctx_item['id']}")

            # Si c'est un work item, charger l'objet complet
            if ctx_item['type'] == 'work_item':
                work_item_id = ctx_item['id']
                project_id = state['project_id']

                try:
                    logger.info(f"[ENTRY_NODE] Loading full work item: {work_item_id}")
                    storage = ProjectContextService()
                    existing_items = storage.load_context(project_id)

                    # Trouver le work item correspondant
                    for item in existing_items:
                        if item.id == work_item_id:
                            context_work_item = item
                            logger.info(f"[ENTRY_NODE] Work item loaded: {item.title}")
                            logger.info(f"[ENTRY_NODE] Description: {item.description[:100] if item.description else 'N/A'}...")
                            break

                    if not context_work_item:
                        logger.warning(f"[ENTRY_NODE] Work item {work_item_id} not found in backlog")

                except Exception as e:
                    logger.error(f"[ENTRY_NODE] Error loading work item: {e}", exc_info=True)
    else:
        logger.info("[ENTRY_NODE] No context provided")

    # Envoyer un événement de timeline pour le début du workflow
    thread_id = state.get("thread_id", "")
    if thread_id:
        timeline_service = get_timeline_service()
        event = TimelineEvent(
            type="WORKFLOW_START",
            message=f"Processing query for project {state['project_id']}",
            status="IN_PROGRESS",
            details={
                "project_id": state["project_id"],
                "user_query": state["user_query"],
            },
        )
        timeline_service.add_event(thread_id, event)

    # Retourner le work item chargé (ou None)
    result = {}
    if context_work_item:
        result["context_work_item"] = context_work_item

    return result


def task_rewriter_node(state: GraphState) -> dict[str, Any]:
    """
    Reformule la requête utilisateur en une tâche claire et explicite.

    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec la tâche reformulée
    """
    logger.info("[TASK_REWRITER_NODE] Rewriting user query into explicit task...")

    # Charger le prompt
    prompt_config = load_task_rewriter_prompt()

    # Créer le résumé du contexte
    context = state.get("context", [])
    context_summary = "Aucun"

    if context and len(context) > 0:
        context_parts = []
        for ctx_item in context:
            ctx_type = ctx_item.get("type", "unknown")
            ctx_id = ctx_item.get("id", "unknown")
            ctx_name = ctx_item.get("name", "")

            if ctx_type == "work_item":
                context_parts.append(f"work_item '{ctx_id}' - '{ctx_name}'")
            elif ctx_type == "document":
                context_parts.append(f"document '{ctx_name}'")
            else:
                context_parts.append(f"{ctx_type} '{ctx_id}'")

        context_summary = ", ".join(context_parts)
        logger.info(f"[TASK_REWRITER_NODE] Context summary: {context_summary}")
    else:
        logger.info("[TASK_REWRITER_NODE] No context provided")

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].replace(
        "{{ context_summary }}", context_summary
    ).replace(
        "{{ user_query }}", state["user_query"]
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    logger.info(f"[TASK_REWRITER_NODE] Using model: {model}")

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

        # Extraire la réponse (tâche reformulée)
        rewritten_task = response.choices[0].message.content.strip()

        logger.info(f"[TASK_REWRITER_NODE] Rewritten task: {rewritten_task}")

        # Envoyer un événement de timeline pour la tâche reformulée
        thread_id = state.get("thread_id", "")
        if thread_id:
            timeline_service = get_timeline_service()
            event = TimelineEvent(
                type="TASK_REWRITTEN",
                message=f"Rewritten task: '{rewritten_task}'",
                status="SUCCESS",
                details={"rewritten_task": rewritten_task},
            )
            timeline_service.add_event(thread_id, event)

        return {
            "rewritten_task": rewritten_task,
        }

    except Exception as e:
        logger.error("[TASK_REWRITER_NODE] Error calling LLM.", exc_info=True)
        # Fallback: utiliser la requête originale
        return {
            "rewritten_task": state["user_query"],
        }


def router_node(state: GraphState) -> dict[str, Any]:
    """
    Route la requête vers le bon agent selon la tâche reformulée.

    Utilise un LLM avec des exemples few-shot pour déterminer
    quel agent et quelle tâche exécuter, ainsi que les arguments nécessaires.


    Détecte également les ambiguïtés potentielles dans la requête utilisateur.


    Args:
        state: État actuel du graphe

    Returns:
        Mise à jour partielle de l'état avec next_node, agent_id, agent_task et intent_args
    """
    rewritten_task = state.get("rewritten_task", "")

    user_response = state.get("user_response", "")

    # Si on a une réponse utilisateur, combiner avec la tâche originale
    if user_response:
        logger.info(f"[ROUTER_NODE] User response provided: {user_response}")
        # Combiner la tâche originale avec la réponse pour former une requête complète
        rewritten_task = f"{rewritten_task} {user_response}"
        logger.info(f"[ROUTER_NODE] Combined task: {rewritten_task}")


    logger.info(f"[ROUTER_NODE] Routing based on rewritten task: {rewritten_task}")

    # Envoyer un événement de timeline pour le début du routage
    thread_id = state.get("thread_id", "")
    if thread_id:
        timeline_service = get_timeline_service()
        event = TimelineEvent(
            type="ROUTER_DECIDING",
            message="Router analyzing task and deciding which agent to use...",
            status="IN_PROGRESS",
        )
        timeline_service.add_event(thread_id, event)

    if not rewritten_task:
        logger.warning("[ROUTER_NODE] No rewritten task found, routing to end")
        return {
            "next_node": "end",
            "agent_id": "none",
            "agent_task": "none",
            "result": "No task to process.",
        }

    # DÉTECTION D'AMBIGUÏTÉ (Simulation pour le MVP)
    # Vérifier si la requête contient "Tc" ou "test" et s'il y a plusieurs work items
    ambiguous = False
    context = state.get("context", [])
    user_query = state.get("user_query", "")

    if context and len(context) > 0:
        # Vérifier si la requête mentionne des cas de test
        query_lower = user_query.lower()
        if "tc" in query_lower or "test" in query_lower or "cas de test" in query_lower:
            # Compter les work items dans le contexte
            work_items = [item for item in context if item.get("type") == "work_item"]
            if len(work_items) > 1:
                logger.info(f"[ROUTER_NODE] Ambiguity detected: {len(work_items)} work items found")
                ambiguous = True

    # Si ambiguïté détectée, marquer l'état et continuer le routage normal
    # La fonction de routage conditionnel décidera ensuite
    if ambiguous:
        logger.info("[ROUTER_NODE] Setting ambiguous_intent flag")
        # Retourner immédiatement pour router vers le nœud de clarification
        return {
            "ambiguous_intent": True,
            "next_node": "clarification",
        }

    # Charger le prompt
    prompt_config = load_router_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].replace(
        "{{ rewritten_task }}", rewritten_task
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    logger.info(f"[ROUTER_NODE] Using model: {model}")

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

        # Extraire la réponse (JSON de routage avec Chain of Thought)
        routing_json_str = response.choices[0].message.content.strip()

        logger.debug(f"[ROUTER_NODE] Raw LLM response: {routing_json_str}")

        # Nettoyer la chaîne pour extraire uniquement le JSON
        # (enlever les balises markdown comme ```json si présentes)
        try:
            start_index = routing_json_str.index('{')
            end_index = routing_json_str.rindex('}') + 1
            clean_json_str = routing_json_str[start_index:end_index]
            logger.debug(f"[ROUTER_NODE] Cleaned JSON string: {clean_json_str}")
        except ValueError as e:
            # Si '{' ou '}' ne sont pas trouvés, on essaie avec la chaîne brute
            logger.warning(f"[ROUTER_NODE] Could not find JSON delimiters in response: {e}")
            clean_json_str = routing_json_str

        logger.info(f"[ROUTER_NODE] JSON to parse: {clean_json_str}")

        # Parser le JSON dans un objet RouterDecision
        routing_data = json.loads(clean_json_str)
        router_decision = RouterDecision(**routing_data)

        # Valider la structure de la décision
        router_decision.validate_decision()

        # LOG CRUCIAL: Afficher la chaîne de pensée du routeur
        logger.info(f"[ROUTER_THOUGHT] {router_decision.thought}")

        # Envoyer un événement de timeline pour la pensée du routeur
        if thread_id:
            event = TimelineEvent(
                type="ROUTER_THOUGHT",
                message=f"Router thought: '{router_decision.thought}'",
                status="IN_PROGRESS",
                details={"thought": router_decision.thought},
            )
            timeline_service.add_event(thread_id, event)

        # Extraire les éléments de la décision
        agent_id = router_decision.decision.get("agent", "backlog_agent")
        agent_task = router_decision.decision.get("task", "decompose_objective")
        args = router_decision.decision.get("args", {})

        # Normaliser le nom de l'agent (robustesse contre les variations de casse)
        # Map des variations possibles vers le nom canonique en snake_case
        agent_id_map = {
            "epicarchitectagent": "epic_architect_agent",
            "epic_architect_agent": "epic_architect_agent",
            "storytelleragent": "story_teller_agent",
            "story_teller_agent": "story_teller_agent",
            "backlogagent": "backlog_agent",
            "backlog_agent": "backlog_agent",
            "testagent": "test_agent",
            "test_agent": "test_agent",
            "documentagent": "document_agent",
            "document_agent": "document_agent",
            "diagrammasteragent": "diagram_master_agent",
            "diagram_master_agent": "diagram_master_agent",
            "fallbackagent": "fallback_agent",
            "fallback_agent": "fallback_agent",
        }

        # Normaliser en minuscule et sans underscores pour la clé de lookup
        normalized_key = agent_id.lower().replace("_", "")
        if normalized_key in agent_id_map:
            original_agent_id = agent_id
            agent_id = agent_id_map[normalized_key]
            if original_agent_id != agent_id:
                logger.info(f"[ROUTER_NODE] Normalized agent name from '{original_agent_id}' to '{agent_id}'")

        logger.info(f"[ROUTER_NODE] Selected agent: {agent_id}")
        logger.info(f"[ROUTER_NODE] Selected task: {agent_task}")
        logger.info(f"[ROUTER_NODE] Extracted args: {args}")

        # Envoyer un événement de timeline pour la décision de routage
        if thread_id:
            event = TimelineEvent(
                type="ROUTER_DECISION",
                message=f"Routing to agent: {agent_id} (task: {agent_task})",
                status="SUCCESS",
                agent_name=agent_id,
                details={
                    "agent_id": agent_id,
                    "agent_task": agent_task,
                    "args": args,
                },
            )
            timeline_service.add_event(thread_id, event)

        # Vérifier si une clarification est nécessaire
        # Par exemple, si generate_test_cases ou generate_acceptance_criteria
        # sans item_id spécifié
        clarification_needed = False
        clarification_question = ""

        if agent_task in ["generate_test_cases", "generate_acceptance_criteria", "improve_description"]:
            if not args.get("item_id"):
                clarification_needed = True
                task_translations = {
                    "generate_test_cases": "générer les cas de test",
                    "generate_acceptance_criteria": "générer les critères d'acceptation",
                    "improve_description": "améliorer la description",
                }
                task_label = task_translations.get(agent_task, "effectuer cette opération")
                clarification_question = f"Pour quel work item souhaitez-vous {task_label} ? Veuillez préciser l'identifiant (ex: FIR-3, US-001)."

        if clarification_needed:
            logger.info(f"[ROUTER_NODE] Clarification needed: {clarification_question}")
            return {
                "next_node": "end",
                "agent_id": "none",
                "agent_task": "none",
                "clarification_needed": True,
                "clarification_question": clarification_question,
                "status": "clarification_needed",
                "result": "Clarification requise avant de continuer.",
            }

        logger.info("[ROUTER_NODE] Routing to agent node")

        return {
            "next_node": "agent",
            "agent_id": agent_id,
            "agent_task": agent_task,
            "intent": {
                "args": args
            },
            "intent_args": args,  # Ajouter intent_args pour compatibilité avec les agents
        }

    except json.JSONDecodeError as e:
        logger.error(f"[ROUTER_NODE] JSON parsing error: {e}", exc_info=True)
        if 'routing_json_str' in locals():
            logger.error(f"[ROUTER_NODE] Invalid JSON received: {routing_json_str}")

        # Fallback: utiliser le fallback_agent pour gérer l'erreur
        logger.warning("[ROUTER_NODE] Falling back to fallback_agent due to JSON parsing error")
        return {
            "next_node": "fallback",
            "agent_id": "fallback_agent",
            "agent_task": "handle_unknown_intent",
            "intent": {"args": {}},
            "intent_args": {},
        }

    except (KeyError, ValueError) as e:
        logger.error(f"[ROUTER_NODE] RouterDecision validation error: {e}", exc_info=True)
        if 'routing_json_str' in locals():
            logger.error(f"[ROUTER_NODE] Invalid RouterDecision structure: {routing_json_str}")

        # Fallback: utiliser le fallback_agent pour gérer l'erreur de validation
        logger.warning("[ROUTER_NODE] Falling back to fallback_agent due to validation error")
        return {
            "next_node": "fallback",
            "agent_id": "fallback_agent",
            "agent_task": "handle_unknown_intent",
            "intent": {"args": {}},
            "intent_args": {},
        }

    except Exception as e:
        logger.error(f"[ROUTER_NODE] Unexpected error: {e}", exc_info=True)
        if 'routing_json_str' in locals():
            logger.error(f"[ROUTER_NODE] LLM response was: {routing_json_str}")

        # Fallback: utiliser le fallback_agent pour gérer toute autre erreur
        logger.warning("[ROUTER_NODE] Falling back to fallback_agent due to unexpected error")
        return {
            "next_node": "fallback",
            "agent_id": "fallback_agent",
            "agent_task": "handle_unknown_intent",
            "intent": {"args": {}},
            "intent_args": {},
        }


def route_after_router(
    state: GraphState,
) -> Literal["ask_for_clarification", "agent", "fallback", "end"]:
    """
    Fonction de routage conditionnel après le router_node.

    Vérifie si une ambiguïté a été détectée dans la requête utilisateur.
    Si oui, route vers le nœud de clarification.
    Vérifie également si le routeur a sélectionné le fallback_agent.
    Si oui, route vers le nœud de fallback.
    Sinon, continue vers l'agent ou la fin selon next_node.

    Args:
        state: État actuel du graphe

    Returns:
        Nom du prochain nœud ("ask_for_clarification", "agent", "fallback", ou "end")
    """
    # Vérifier si une ambiguïté a été détectée
    ambiguous_intent = state.get("ambiguous_intent", False)
    next_node = state.get("next_node", "end")
    agent_id = state.get("agent_id", "")

    if ambiguous_intent:
        logger.info("[ROUTE_AFTER_ROUTER] Ambiguity detected, routing to clarification")
        return "ask_for_clarification"

    # Vérifier si le routeur a sélectionné le fallback_agent
    if agent_id == "fallback_agent":
        logger.info("[ROUTE_AFTER_ROUTER] Fallback agent selected, routing to fallback")
        return "fallback"

    # Sinon, router normalement
    if next_node == "agent":
        logger.info("[ROUTE_AFTER_ROUTER] Routing to agent")
        return "agent"

    logger.info("[ROUTE_AFTER_ROUTER] Routing to end")
    return "end"


def should_continue_to_agent(
    state: GraphState,
) -> Literal["agent", "end"]:
    """
    Fonction de routage conditionnel depuis le router (version legacy).

    DEPRECATED: Utilisez route_after_router à la place.

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

    logger.info("[AGENT_NODE] Routing to specific agent...")
    logger.info(f"[AGENT_NODE] Agent ID: {agent_id}")
    logger.info(f"[AGENT_NODE] Agent task: {agent_task}")

    # Envoyer un événement de timeline pour le début de l'exécution de l'agent
    thread_id = state.get("thread_id", "")
    if thread_id:
        timeline_service = get_timeline_service()
        event = TimelineEvent(
            type="AGENT_START",
            agent_name=agent_id,
            message=f"Agent {agent_id} starting task: {agent_task}",
            status="IN_PROGRESS",
            details={"agent_task": agent_task},
        )
        timeline_service.add_event(thread_id, event)

    # Dispatcher vers le bon agent selon agent_id
    result = {}
    if agent_id == "backlog_agent":
        # Router vers la méthode appropriée du backlog_agent
        if agent_task == "decompose_objective":
            result = backlog_agent.decompose_objective(state)
        elif agent_task == "review_quality":
            result = backlog_agent.review_quality(state)
        elif agent_task == "improve_description":
            result = backlog_agent.improve_description(state)
        elif agent_task == "generate_acceptance_criteria":
            result = backlog_agent.generate_acceptance_criteria(state)
        elif agent_task == "generate_specification":
            result = {
                "status": "completed",
                "result": "Stub: Generating detailed specification (not yet implemented)",
            }
        elif agent_task == "search_requirements":
            result = {
                "status": "completed",
                "result": "Stub: Searching requirements (not yet implemented)",
            }
        elif agent_task == "estimate_stories":
            result = {
                "status": "completed",
                "result": "Stub: Estimating story points (not yet implemented)",
            }
        else:
            result = {
                "status": "error",
                "result": f"Unknown task '{agent_task}' for backlog_agent",
            }

    elif agent_id == "epic_architect_agent":
        # Router vers la méthode appropriée de l'epic_architect_agent
        if agent_task == "generate_epics":
            result = epic_architect_agent.generate_epics(state)
        else:
            result = {
                "status": "error",
                "result": f"Unknown task '{agent_task}' for epic_architect_agent",
            }

    elif agent_id == "story_teller_agent":
        # Router vers la méthode appropriée du story_teller_agent
        if agent_task == "decompose_feature_into_stories":
            result = story_teller_agent.decompose_feature_into_stories(state)
        else:
            result = {
                "status": "error",
                "result": f"Unknown task '{agent_task}' for story_teller_agent",
            }

    elif agent_id == "document_agent":
        # Router vers la méthode appropriée du document_agent
        if agent_task == "extract_features":
            result = document_agent.extract_requirements(state)
        else:
            result = {
                "status": "error",
                "result": f"Unknown task '{agent_task}' for document_agent",
            }

    elif agent_id == "test_agent":
        # Router vers la méthode appropriée du test_agent
        if agent_task == "generate_test_cases":
            result = test_agent.generate_test_cases(state)
        else:
            result = {
                "status": "error",
                "result": f"Unknown task '{agent_task}' for test_agent",
            }

    elif agent_id == "diagram_master_agent":
        # Router vers la méthode appropriée du diagram_master_agent
        if agent_task == "generate_diagram":
            result = diagram_master_agent.generate_diagram(state)
        else:
            result = {
                "status": "error",
                "result": f"Unknown task '{agent_task}' for diagram_master_agent",
            }

    else:
        result = {
            "status": "error",
            "result": f"Unknown agent: {agent_id}",
        }

    # Envoyer un événement de timeline pour la fin de l'exécution de l'agent
    if thread_id:
        agent_status = result.get("status", "completed")
        event_status = "SUCCESS" if agent_status in ["completed", "awaiting_approval"] else "ERROR"
        event = TimelineEvent(
            type="AGENT_COMPLETE",
            agent_name=agent_id,
            message=f"Agent {agent_id} completed with status: {agent_status}",
            status=event_status,
            details={
                "agent_task": agent_task,
                "agent_status": agent_status,
            },
        )
        timeline_service.add_event(thread_id, event)

    return result


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
    logger.info("[APPROVAL_NODE] Processing approval decision...")

    approval_decision = state.get("approval_decision")
    project_id = state.get("project_id", "")

    if approval_decision is None:
        logger.info("[APPROVAL_NODE] No approval decision found, workflow interrupted")
        return {
            "status": "interrupted",
            "result": "Workflow interrupted, awaiting approval decision",
        }

    if not approval_decision:
        logger.info("[APPROVAL_NODE] ImpactPlan rejected by user")
        return {
            "status": "rejected",
            "result": "ImpactPlan rejected. No changes were applied to the backlog.",
        }

    # L'utilisateur a approuvé, on applique l'ImpactPlan
    logger.info("[APPROVAL_NODE] ImpactPlan approved by user, applying changes...")

    impact_plan = state.get("impact_plan", {})
    new_items = impact_plan.get("new_items", [])
    modified_items = impact_plan.get("modified_items", [])
    deleted_items = impact_plan.get("deleted_items", [])

    logger.info(f"[APPROVAL_NODE] Changes to apply: {len(new_items)} new, "
                f"{len(modified_items)} modified, {len(deleted_items)} deleted")

    # Charger le backlog existant
    storage = ProjectContextService()

    try:
        existing_items = storage.load_context(project_id)
        logger.info(f"[APPROVAL_NODE] Loaded {len(existing_items)} existing work items")
    except FileNotFoundError:
        existing_items = []
        logger.info("[APPROVAL_NODE] No existing backlog found, starting fresh")

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
                    logger.info(f"[APPROVAL_NODE] Updated item {after_item.id}")
                    break

    # Gérer les deleted_items (supprimer les items par leur ID)
    deleted_ids = set()
    for item_data in deleted_items:
        # L'item peut être un dict avec un champ "id" ou directement un ID string
        if isinstance(item_data, dict):
            item_id = item_data.get("id")
        else:
            item_id = str(item_data)

        if item_id:
            deleted_ids.add(item_id)
            logger.info(f"[APPROVAL_NODE] Marking item {item_id} for deletion")

    # Filtrer les items supprimés de existing_items
    if deleted_ids:
        existing_items = [item for item in existing_items if item.id not in deleted_ids]
        logger.info(f"[APPROVAL_NODE] Removed {len(deleted_ids)} items from backlog")

    # Construire le nouveau backlog complet
    updated_backlog = existing_items + new_work_items

    logger.info(f"[APPROVAL_NODE] New backlog size: {len(updated_backlog)} work items")

    # Sauvegarder le nouveau backlog (crée une nouvelle version)
    storage.save_backlog(project_id, updated_backlog)

    # Déterminer le numéro de version qui a été créé
    latest_version = storage._find_latest_backlog_version(project_id)

    logger.info(f"[APPROVAL_NODE] Successfully saved backlog_v{latest_version}.json")

    result_parts = []
    if len(new_work_items) > 0:
        result_parts.append(f"Added {len(new_work_items)} new work items")
    if modified_count > 0:
        result_parts.append(f"Modified {modified_count} work items")
    if len(deleted_ids) > 0:
        result_parts.append(f"Deleted {len(deleted_ids)} work items")

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
    logger.info("[END_NODE] Workflow completed")
    logger.info(f"[END_NODE] Final result: {state.get('result', 'No result')}")
    logger.info(f"[END_NODE] Status: {state.get('status', 'unknown')}")

    # Envoyer un événement de timeline pour la fin du workflow
    thread_id = state.get("thread_id", "")
    if thread_id:
        timeline_service = get_timeline_service()
        status = state.get("status", "completed")
        result = state.get("result", "No result")

        event_status = "SUCCESS" if status in ["completed", "awaiting_approval", "approved"] else "ERROR"
        event = TimelineEvent(
            type="WORKFLOW_COMPLETE",
            message=f"Workflow completed with status: {status}",
            status=event_status,
            details={
                "status": status,
                "result": result,
            },
        )
        timeline_service.add_event(thread_id, event)

        # Signaler la fin du stream pour cette session
        timeline_service.signal_done(thread_id)

    return {}


# Construction du graphe
workflow = StateGraph(GraphState)

# Ajout des nœuds
workflow.add_node("entry", entry_node)
workflow.add_node("task_rewriter", task_rewriter_node)
workflow.add_node("router", router_node)
workflow.add_node("ask_for_clarification", ask_for_clarification)
workflow.add_node("fallback", handle_unknown_intent)
workflow.add_node("agent", agent_node)
workflow.add_node("approval", approval_node)
workflow.add_node("end", end_node)

# Définition des arêtes (flux)
workflow.set_entry_point("entry")
workflow.add_edge("entry", "task_rewriter")
workflow.add_edge("task_rewriter", "router")

# Routage conditionnel depuis le router
# Utilise route_after_router pour gérer la clarification et le fallback
workflow.add_conditional_edges(
    "router",
    route_after_router,
    {
        "ask_for_clarification": "ask_for_clarification",
        "fallback": "fallback",
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

# Arête depuis le nœud de clarification vers la fin
# Pour ce MVP, le workflow s'arrête après avoir posé la question de clarification
workflow.add_edge("ask_for_clarification", "end")

# Arête depuis le nœud fallback vers la fin
# Le workflow se termine après avoir retourné le message de fallback
workflow.add_edge("fallback", "end")

workflow.add_edge("approval", "end")
workflow.add_edge("end", END)

# Créer un checkpointer en mémoire pour gérer les états interrompus
# Cela permet de reprendre l'exécution après une interruption
checkpointer = MemorySaver()

# Compilation du graphe avec interruption avant le nœud approval
# Cela permet d'attendre la validation humaine avant de continuer
app = workflow.compile(checkpointer=checkpointer, interrupt_before=["approval"])
