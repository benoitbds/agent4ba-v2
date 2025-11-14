/**
 * Types pour les événements SSE du backend Agent4BA
 */

export interface TestCaseStep {
  step: string;
  expected_result: string;
}

export interface TestCase {
  title: string;
  scenario: string;
  steps: TestCaseStep[];
}

export interface WorkItem {
  id: string;
  project_id: string;
  type: "feature" | "story" | "task" | "test_case";
  title: string;
  description: string;
  parent_id: string | null;
  acceptance_criteria?: string[];
  test_cases?: TestCase[];
  validation_status: "ia_generated" | "human_validated" | "ia_modified";
  attributes: {
    priority?: string;
    status?: string;
    points?: number;
    [key: string]: unknown;
  };
}

export interface ContextItem {
  type: "document" | "work_item";
  id: string;
  name: string;
}

export interface ModifiedItem {
  before: WorkItem;
  after: WorkItem;
}

export interface ImpactPlan {
  new_items: WorkItem[];
  modified_items: ModifiedItem[];
  deleted_items: string[];
}

// Base type for all SSE events
export interface BaseEvent {
  type: string;
}

export interface ThreadIdEvent extends BaseEvent {
  type: "thread_id";
  thread_id: string;
}

export interface UserRequestEvent extends BaseEvent {
  type: "user_request";
  query: string;
}

export interface NodeStartEvent extends BaseEvent {
  type: "node_start";
  node_name: string;
}

export interface NodeEndEvent extends BaseEvent {
  type: "node_end";
  node_name: string;
  output?: Record<string, unknown>;
}

export interface LLMStartEvent extends BaseEvent {
  type: "llm_start";
  model?: string;
}

export interface LLMTokenEvent extends BaseEvent {
  type: "llm_token";
  token: string;
}

export interface LLMEndEvent extends BaseEvent {
  type: "llm_end";
  content?: string;
}

export interface ImpactPlanReadyEvent extends BaseEvent {
  type: "impact_plan_ready";
  impact_plan: ImpactPlan;
  thread_id: string;
  status: string;
}

export interface WorkflowCompleteEvent extends BaseEvent {
  type: "workflow_complete";
  result: string;
  status: string;
}

export interface ErrorEvent extends BaseEvent {
  type: "error";
  error: string;
  details?: string;
}

export interface AgentStartEvent extends BaseEvent {
  type: "agent_start";
  thought: string;
  agent_name: string;
}

export interface AgentPlanEvent extends BaseEvent {
  type: "agent_plan";
  steps: string[];
  agent_name: string;
}

export interface ToolUsedEvent extends BaseEvent {
  type: "tool_used";
  tool_run_id: string;
  tool_name: string;
  tool_icon: string;
  description: string;
  status: "running" | "completed" | "error";
  details?: Record<string, unknown>;
}

// Structure pour organiser les événements par session
export interface TimelineSession {
  id: string;
  user_query: string;
  timestamp: Date;
  tool_runs: Map<string, ToolRunState>;
  agent_events: TimelineEvent[];
  is_expanded: boolean;
}

// État d'une exécution d'outil avec ses mises à jour
export interface ToolRunState {
  tool_run_id: string;
  tool_name: string;
  tool_icon: string;
  description: string;
  status: "running" | "completed" | "error";
  details: Record<string, string | number | boolean | null | undefined>;
  started_at: Date;
  completed_at?: Date;
}

// Union type of all possible events
export type SSEEvent =
  | ThreadIdEvent
  | UserRequestEvent
  | NodeStartEvent
  | NodeEndEvent
  | LLMStartEvent
  | LLMTokenEvent
  | LLMEndEvent
  | ImpactPlanReadyEvent
  | WorkflowCompleteEvent
  | ErrorEvent
  | AgentStartEvent
  | AgentPlanEvent
  | ToolUsedEvent;

// For timeline display
export interface TimelineEvent {
  id: string;
  timestamp: Date;
  event: SSEEvent;
}

// Multi-turn conversation types
export interface ClarificationNeededResponse {
  status: "clarification_needed";
  conversation_id: string;
  question: string;
}

export interface ApprovalNeededResponse {
  status: "awaiting_approval";
  thread_id: string;
  impact_plan: ImpactPlan;
}

export interface ExecuteSuccessResponse {
  result: string;
  project_id: string;
  status: string;
}

export interface RespondSuccessResponse {
  result: string;
  project_id: string;
  status: string;
  thread_id: string | null;
  impact_plan: ImpactPlan | null;
}
