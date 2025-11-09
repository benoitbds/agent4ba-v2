/**
 * API utilities for communicating with Agent4BA backend
 */

import type { SSEEvent, WorkItem } from "@/types/events";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

export interface ChatRequest {
  project_id: string;
  query: string;
  document_content?: string;
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
 * Upload a document to a project
 */
export async function uploadDocument(
  projectId: string,
  file: File
): Promise<{ filename: string; message: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/projects/${projectId}/documents`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `HTTP error! status: ${response.status}`
    );
  }

  return response.json();
}
