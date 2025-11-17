/**
 * Types pour les événements de timeline SSE du backend Agent4BA
 * Endpoint: GET /api/v1/timeline/stream/{session_id}
 */

/**
 * Interface pour les événements de timeline reçus via SSE
 * Correspond au modèle Pydantic TimelineEvent du backend
 */
export interface TimelineEvent {
  event_id: string;
  timestamp: string;
  type:
    | 'WORKFLOW_START'
    | 'TASK_REWRITTEN'
    | 'ROUTER_DECIDING'
    | 'ROUTER_THOUGHT'
    | 'ROUTER_DECISION'
    | 'AGENT_START'
    | 'AGENT_COMPLETE'
    | 'WORKFLOW_COMPLETE'
    | 'IMPACT_PLAN_READY'
    | 'CLARIFICATION_NEEDED'
    | 'SCHEMA_CHANGE_PROPOSED'
    | 'ERROR';
  agent_name?: string;
  message: string;
  status: 'IN_PROGRESS' | 'SUCCESS' | 'ERROR' | 'WAITING';
  details?: Record<string, any>;
}
