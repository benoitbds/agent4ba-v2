/**
 * API utilities for communicating with Agent4BA backend
 */

import type { SSEEvent, WorkItem, ContextItem } from "@/types/events";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

export interface ChatRequest {
  project_id: string;
  query: string;
  context?: ContextItem[];
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
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

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
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ approved }),
  });

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
    headers: {
      "Content-Type": "application/json",
    },
  });

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
    headers: {
      "Content-Type": "application/json",
    },
  });

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
    headers: {
      "Content-Type": "application/json",
    },
  });

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
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_id: projectId }),
  });

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
    headers: {
      "Content-Type": "application/json",
    },
  });

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

  const response = await fetch(`${API_URL}/projects/${projectId}/documents`, {
    method: "POST",
    body: formData,
  });

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
    headers: {
      "Content-Type": "application/json",
    },
  });

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
): Promise<void> {
  const response = await fetch(
    `${API_URL}/projects/${projectId}/documents/${encodeURIComponent(documentName)}`,
    {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  // Code 204 No Content - pas de corps de réponse à parser
}

/**
 * Update a WorkItem in the backlog
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
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updatedData),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}
