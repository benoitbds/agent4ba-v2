/**
 * API utilities for communicating with Agent4BA backend
 */

import type {
  SSEEvent,
  WorkItem,
  ContextItem,
  ClarificationNeededResponse,
  ApprovalNeededResponse,
  ExecuteSuccessResponse,
  ExecuteWorkflowResponse,
  RespondSuccessResponse,
  ProjectSchema,
} from "@/types/events";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

/**
 * Custom error class for authentication errors
 */
export class UnauthorizedError extends Error {
  constructor(message: string = "Unauthorized") {
    super(message);
    this.name = "UnauthorizedError";
  }
}

/**
 * Get authentication headers with Bearer token
 */
function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("auth_token");
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

/**
 * Handle API response and check for authentication errors
 * If 401, clear localStorage and throw UnauthorizedError
 */
async function handleResponse(response: Response): Promise<Response> {
  if (response.status === 401) {
    // Clear authentication data from localStorage
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");

    // Throw a specific error that components can catch
    throw new UnauthorizedError("Session expired. Please log in again.");
  }

  return response;
}

export interface ChatRequest {
  project_id: string;
  query: string;
  context?: ContextItem[];
  session_id?: string; // Pour le streaming temps réel des événements
}

export interface ApprovalRequest {
  approved: boolean;
}

/**
 * Stream chat events using fetch and ReadableStream
 * EventSource doesn't support POST, so we use fetch with streaming
 */
export async function* streamChatEvents(
  request: ChatRequest
): AsyncGenerator<SSEEvent, void, unknown> {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Response body is null");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      // Decode the chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete lines
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        // SSE format: "data: {json}"
        if (line.startsWith("data: ")) {
          const jsonStr = line.slice(6); // Remove "data: " prefix
          if (jsonStr.trim()) {
            try {
              const event = JSON.parse(jsonStr) as SSEEvent;
              yield event;
            } catch (e) {
              console.error("Failed to parse SSE event:", e, jsonStr);
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Send approval decision for an ImpactPlan
 */
export async function sendApprovalDecision(
  threadId: string,
  approved: boolean
): Promise<{
  result: string;
  project_id: string;
  status: string;
}> {
  const response = await fetch(`${API_URL}/agent/run/${threadId}/continue`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ approved }),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Get the current backlog for a project
 */
export async function getProjectBacklog(
  projectId: string
): Promise<WorkItem[]> {
  const response = await fetch(`${API_URL}/projects/${projectId}/backlog`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Get the timeline history for a project
 */
export async function getProjectTimelineHistory(
  projectId: string
): Promise<Array<{ timestamp: string; events: SSEEvent[] }>> {
  const response = await fetch(`${API_URL}/projects/${projectId}/timeline`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}
/**
 * Get the list of available projects
 */
export async function getProjects(): Promise<string[]> {
  const response = await fetch(`${API_URL}/projects`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Create a new project
 */
export async function createProject(
  projectId: string
): Promise<{ project_id: string; message: string }> {
  const response = await fetch(`${API_URL}/projects`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ project_id: projectId }),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

/**
 * Get the list of documents for a project
 */
export async function getProjectDocuments(
  projectId: string
): Promise<string[]> {
  const response = await fetch(`${API_URL}/projects/${projectId}/documents`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Upload a document for a project
 */
export async function uploadDocument(
  projectId: string,
  file: File
): Promise<{ message: string; filename: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const token = localStorage.getItem("auth_token");
  const headers: HeadersInit = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}/projects/${projectId}/documents`, {
    method: "POST",
    headers: headers,
    body: formData,
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    // Gérer spécifiquement l'erreur 413 (Content Too Large)
    if (response.status === 413) {
      throw new Error("Le fichier dépasse la taille maximale autorisée de 50 Mo.");
    }

    // Tenter de parser l'erreur JSON du backend
    try {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    } catch {
      // Si le parsing JSON échoue, lever une erreur générique
      throw new Error(`Erreur lors de l'upload du fichier (${response.status})`);
    }
  }

  return response.json();
}

/**
 * Delete a project and all its associated data
 */
export async function deleteProject(projectId: string): Promise<void> {
  const response = await fetch(`${API_URL}/projects/${projectId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }
}

/**
 * Delete a document from a project
 */
export async function deleteDocument(
  projectId: string,
  documentName: string
): Promise<{ message: string }> {
  const response = await fetch(
    `${API_URL}/projects/${projectId}/documents/${encodeURIComponent(documentName)}`,
    {
      method: "DELETE",
      headers: getAuthHeaders(),
    }
  );

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

/**
 * Update a WorkItem in the backlog (partial update - title and description only)
 */
export async function updateWorkItem(
  projectId: string,
  itemId: string,
  updatedData: { title: string; description: string | null }
): Promise<WorkItem> {
  const response = await fetch(
    `${API_URL}/projects/${projectId}/backlog/${itemId}`,
    {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify(updatedData),
    }
  );

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

/**
 * Update a complete WorkItem (including diagrams, acceptance criteria, etc.)
 */
export async function updateFullWorkItem(
  projectId: string,
  itemId: string,
  updatedWorkItem: WorkItem
): Promise<WorkItem> {
  const response = await fetch(
    `${API_URL}/projects/${projectId}/work_items/${itemId}`,
    {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify(updatedWorkItem),
    }
  );

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

/**
 * Validate a WorkItem (mark as human-validated)
 */
export async function validateWorkItem(
  projectId: string,
  itemId: string
): Promise<WorkItem> {
  const response = await fetch(
    `${API_URL}/projects/${projectId}/backlog/${itemId}/validate`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    }
  );

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

/**
 * Generate acceptance criteria for a WorkItem
 */
export async function generateAcceptanceCriteria(
  projectId: string,
  itemId: string
): Promise<WorkItem> {
  const response = await fetch(
    `${API_URL}/projects/${projectId}/work_items/${itemId}/generate-acceptance-criteria`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    }
  );

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

/**
 * Generate test cases for a WorkItem
 */
export async function generateTestCases(
  projectId: string,
  itemId: string
): Promise<WorkItem> {
  const response = await fetch(
    `${API_URL}/projects/${projectId}/work_items/${itemId}/generate-test-cases`,
    {
      method: "POST",
      headers: getAuthHeaders(),
    }
  );

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

/**
 * Create a new WorkItem
 */
export async function createWorkItem(
  projectId: string,
  workItemData: {
    type: string;
    title: string;
    description: string | null;
    parent_id?: string | null;
    acceptance_criteria?: string[];
  }
): Promise<WorkItem> {
  const response = await fetch(
    `${API_URL}/projects/${projectId}/work_items`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(workItemData),
    }
  );

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

/**
 * Delete a WorkItem from the backlog
 */
export async function deleteWorkItem(
  projectId: string,
  itemId: string
): Promise<void> {
  const response = await fetch(
    `${API_URL}/projects/${projectId}/work_items/${itemId}`,
    {
      method: "DELETE",
      headers: getAuthHeaders(),
    }
  );

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }
}

/**
 * Execute a workflow asynchronously in the background
 * Always returns HTTP 202 Accepted with a session_id for real-time SSE streaming
 * The client should connect to /api/v1/timeline/stream/{session_id} to receive events
 */
export async function executeWorkflow(
  request: ChatRequest
): Promise<ExecuteWorkflowResponse> {
  const response = await fetch(`${API_URL}/execute`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok || response.status !== 202) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Respond to a clarification request and resume the workflow
 */
export async function respondToClarification(
  conversationId: string,
  userResponse: string
): Promise<RespondSuccessResponse> {
  const response = await fetch(`${API_URL}/respond`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      conversation_id: conversationId,
      user_response: userResponse,
    }),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Get the current schema for a project
 */
export async function getProjectSchema(
  projectId: string
): Promise<ProjectSchema> {
  const response = await fetch(`${API_URL}/projects/${projectId}/schema`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Update the schema for a project
 */
export async function updateProjectSchema(
  projectId: string,
  schema: ProjectSchema
): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/projects/${projectId}/schema`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(schema),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}

/**
 * Continue the workflow after schema approval
 */
export async function continueAfterSchemaApproval(
  threadId: string,
  approved: boolean
): Promise<{ result: string; status: string }> {
  const response = await fetch(`${API_URL}/agent/run/${threadId}/continue`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ approved }),
  });

  // Check for 401 errors
  await handleResponse(response);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}
