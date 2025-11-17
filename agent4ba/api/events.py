"""
Schémas d'événements pour le streaming SSE.

Ce module définit les structures de données pour les événements
envoyés au client via Server-Sent Events (SSE).
"""

from typing import Any

from pydantic import BaseModel, Field


class StreamEvent(BaseModel):
    """Base class pour tous les événements SSE."""

    type: str = Field(..., description="Type de l'événement")


class ThreadIdEvent(StreamEvent):
    """Événement envoyé au début du stream avec l'identifiant de thread."""

    type: str = Field(default="thread_id", description="Type d'événement")
    thread_id: str = Field(..., description="Identifiant unique du thread de conversation")


class UserRequestEvent(StreamEvent):
    """Événement contenant la requête initiale de l'utilisateur."""

    type: str = Field(default="user_request", description="Type d'événement")
    query: str = Field(..., description="Requête de l'utilisateur")


class NodeStartEvent(StreamEvent):
    """Événement indiquant le début d'exécution d'un nœud."""

    type: str = Field(default="node_start", description="Type d'événement")
    node_name: str = Field(..., description="Nom du nœud qui démarre")


class NodeEndEvent(StreamEvent):
    """Événement indiquant la fin d'exécution d'un nœud."""

    type: str = Field(default="node_end", description="Type d'événement")
    node_name: str = Field(..., description="Nom du nœud qui se termine")
    output: dict[str, Any] | None = Field(
        default=None,
        description="Données de sortie du nœud",
    )


class LLMStartEvent(StreamEvent):
    """Événement indiquant le début d'un appel LLM."""

    type: str = Field(default="llm_start", description="Type d'événement")
    model: str | None = Field(None, description="Nom du modèle LLM utilisé")


class LLMTokenEvent(StreamEvent):
    """Événement contenant un token streamé du LLM."""

    type: str = Field(default="llm_token", description="Type d'événement")
    token: str = Field(..., description="Token généré par le LLM")


class LLMEndEvent(StreamEvent):
    """Événement indiquant la fin d'un appel LLM."""

    type: str = Field(default="llm_end", description="Type d'événement")
    content: str | None = Field(None, description="Contenu complet généré par le LLM")


class ImpactPlanReadyEvent(StreamEvent):
    """Événement envoyé quand un ImpactPlan est prêt pour validation."""

    type: str = Field(default="impact_plan_ready", description="Type d'événement")
    impact_plan: dict[str, Any] = Field(..., description="Plan d'impact généré")
    thread_id: str = Field(..., description="Identifiant du thread pour validation")
    status: str = Field(
        default="awaiting_approval",
        description="Statut du workflow",
    )


class SchemaChangeReadyEvent(StreamEvent):
    """Événement envoyé quand un changement de schéma est prêt pour validation."""

    type: str = Field(default="schema_change_proposed", description="Type d'événement")
    proposed_schema: dict[str, Any] = Field(..., description="Nouveau schéma proposé")
    thread_id: str = Field(..., description="Identifiant du thread pour validation")
    status: str = Field(
        default="awaiting_schema_approval",
        description="Statut du workflow",
    )


class WorkflowCompleteEvent(StreamEvent):
    """Événement indiquant la fin du workflow."""

    type: str = Field(default="workflow_complete", description="Type d'événement")
    result: str = Field(..., description="Résultat final du workflow")
    status: str = Field(..., description="Statut final")


class ErrorEvent(StreamEvent):
    """Événement indiquant une erreur pendant l'exécution."""

    type: str = Field(default="error", description="Type d'événement")
    error: str = Field(..., description="Message d'erreur")
    details: str | None = Field(None, description="Détails supplémentaires sur l'erreur")


class AgentStartEvent(StreamEvent):
    """Événement émis au début de l'exécution d'un agent avec sa reformulation."""

    type: str = Field(default="agent_start", description="Type d'événement")
    thought: str = Field(..., description="Reformulation de ce que l'agent a compris et va faire")
    agent_name: str = Field(..., description="Nom de l'agent qui démarre")


class AgentPlanEvent(StreamEvent):
    """Événement contenant le plan d'action de l'agent."""

    type: str = Field(default="agent_plan", description="Type d'événement")
    steps: list[str] = Field(..., description="Liste des étapes prévues par l'agent")
    agent_name: str = Field(..., description="Nom de l'agent")


class ToolUsedEvent(StreamEvent):
    """Événement indiquant l'utilisation d'un outil par l'agent."""

    type: str = Field(default="tool_used", description="Type d'événement")
    tool_run_id: str = Field(..., description="Identifiant unique de cette exécution d'outil (UUID)")
    tool_name: str = Field(..., description="Nom de l'outil utilisé")
    tool_icon: str = Field(..., description="Emoji/icône représentant l'outil")
    description: str = Field(..., description="Description de ce que fait l'outil")
    status: str = Field(default="running", description="Statut: running, completed, error")
    details: dict[str, Any] | None = Field(None, description="Détails additionnels sur l'utilisation de l'outil")
