"use client";

import { useState, useEffect } from "react";
import { useTranslations } from 'next-intl';
import ChatInput from "@/components/ChatInput";
import TimelineView from "@/components/TimelineView";
import ImpactPlanModal from "@/components/ImpactPlanModal";
import CreateProjectModal from "@/components/CreateProjectModal";
import DeleteProjectModal from "@/components/DeleteProjectModal";
import BacklogView from "@/components/BacklogView";
import ProjectSelector from "@/components/ProjectSelector";
import DocumentManager from "@/components/DocumentManager";
import { streamChatEvents, sendApprovalDecision, getProjectBacklog, getProjects, getProjectDocuments, getProjectTimelineHistory, createProject, deleteProject } from "@/lib/api";
import type { TimelineSession, ToolRunState, ImpactPlan, SSEEvent, WorkItem, ToolUsedEvent, TimelineEvent } from "@/types/events";

export default function Home() {
  const t = useTranslations();
  const [projects, setProjects] = useState<string[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [backlogItems, setBacklogItems] = useState<WorkItem[]>([]);
  const [documents, setDocuments] = useState<string[]>([]);
  const [sessions, setSessions] = useState<TimelineSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [impactPlan, setImpactPlan] = useState<ImpactPlan | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isLoadingBacklog, setIsLoadingBacklog] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isCreateProjectModalOpen, setIsCreateProjectModalOpen] = useState(false);
  const [isDeleteProjectModalOpen, setIsDeleteProjectModalOpen] = useState(false);

  // Load projects list on component mount
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const projectsList = await getProjects();
        setProjects(projectsList);
        // Initialize with first project if available
        if (projectsList.length > 0) {
          setSelectedProject(projectsList[0]);
        }
      } catch (error) {
        console.error("Error loading projects:", error);
      }
    };

    loadProjects();
  }, []);

  // Load backlog when selected project changes
  useEffect(() => {
    if (!selectedProject) return;

    const loadBacklog = async () => {
      setIsLoadingBacklog(true);
      try {
        const items = await getProjectBacklog(selectedProject);
        setBacklogItems(items);
      } catch (error) {
        console.error("Error loading backlog:", error);
        setBacklogItems([]);
      } finally {
        setIsLoadingBacklog(false);
      }
    };

    loadBacklog();
  }, [selectedProject]);

  // Load documents when selected project changes
  useEffect(() => {
    if (!selectedProject) return;

    const loadDocuments = async () => {
      setIsLoadingDocuments(true);
      try {
        const docs = await getProjectDocuments(selectedProject);
        setDocuments(docs);
      } catch (error) {
        console.error("Error loading documents:", error);
        setDocuments([]);
      } finally {
        setIsLoadingDocuments(false);
      }
    };

    loadDocuments();
  }, [selectedProject]);

  // Load timeline history when selected project changes
  useEffect(() => {
    if (!selectedProject) return;

    const loadTimelineHistory = async () => {
      try {
        const history = await getProjectTimelineHistory(selectedProject);

        // Convert history to sessions
        const historySessions: TimelineSession[] = history.map((historySession, index) => {
          const sessionTimestamp = new Date(historySession.timestamp);
          const sessionId = `history-${sessionTimestamp.getTime()}-${index}`;

          // Extract user_query from events
          const userRequestEvent = historySession.events.find((evt: SSEEvent) => evt.type === "user_request");
          const userQuery = userRequestEvent && "query" in userRequestEvent ? userRequestEvent.query : t('agentTimeline.historicalSession');

          // Process tool_used events into tool_runs Map
          const toolRunsMap = new Map<string, ToolRunState>();
          const agentEvents: TimelineEvent[] = [];

          historySession.events.forEach((evt: SSEEvent, eventIndex: number) => {
            if (evt.type === "tool_used") {
              const toolEvent = evt as ToolUsedEvent;
              const existingToolRun = toolRunsMap.get(toolEvent.tool_run_id);

              if (!existingToolRun) {
                // First time seeing this tool_run_id
                toolRunsMap.set(toolEvent.tool_run_id, {
                  tool_run_id: toolEvent.tool_run_id,
                  tool_name: toolEvent.tool_name,
                  tool_icon: toolEvent.tool_icon,
                  description: toolEvent.description,
                  status: toolEvent.status,
                  details: (toolEvent.details || {}) as Record<string, string | number | boolean | null | undefined>,
                  started_at: sessionTimestamp,
                  completed_at: toolEvent.status !== "running" ? sessionTimestamp : undefined,
                });
              } else {
                // Update existing tool_run
                toolRunsMap.set(toolEvent.tool_run_id, {
                  ...existingToolRun,
                  status: toolEvent.status,
                  details: { ...existingToolRun.details, ...(toolEvent.details || {}) } as Record<string, string | number | boolean | null | undefined>,
                  completed_at: toolEvent.status !== "running" ? sessionTimestamp : existingToolRun.completed_at,
                });
              }
            } else if (evt.type === "agent_start" || evt.type === "agent_plan") {
              agentEvents.push({
                id: `${sessionId}-agent-${eventIndex}`,
                timestamp: sessionTimestamp,
                event: evt,
              });
            }
          });

          return {
            id: sessionId,
            user_query: userQuery,
            timestamp: sessionTimestamp,
            tool_runs: toolRunsMap,
            agent_events: agentEvents,
            is_expanded: false, // Historical sessions start collapsed
          };
        });

        // Réinitialiser la timeline avec l'historique du nouveau projet
        setSessions(historySessions);
      } catch (error) {
        console.error("Error loading timeline history:", error);
        // En cas d'erreur, réinitialiser la timeline à vide
        setSessions([]);
      }
    };

    loadTimelineHistory();
  }, [selectedProject]);

  // Function to refresh documents list after upload
  const handleDocumentUploadSuccess = async () => {
    try {
      const docs = await getProjectDocuments(selectedProject);
      setDocuments(docs);
    } catch (error) {
      console.error("Error refreshing documents:", error);
    }
  };

  // Helper function to add or update events in the current session
  const addEventToCurrentSession = (event: SSEEvent, sessionId: string) => {
    setSessions((prevSessions) => {
      return prevSessions.map((session) => {
        // Ne modifier que la session courante
        if (session.id !== sessionId) {
          return session;
        }

        // Créer une nouvelle session avec de nouvelles références immuables
        if (event.type === "tool_used") {
          const toolEvent = event as ToolUsedEvent;
          // Créer une nouvelle Map (copie profonde)
          const newToolRuns = new Map(session.tool_runs);
          const existingToolRun = newToolRuns.get(toolEvent.tool_run_id);

          if (!existingToolRun) {
            // New tool run
            newToolRuns.set(toolEvent.tool_run_id, {
              tool_run_id: toolEvent.tool_run_id,
              tool_name: toolEvent.tool_name,
              tool_icon: toolEvent.tool_icon,
              description: toolEvent.description,
              status: toolEvent.status,
              details: (toolEvent.details || {}) as Record<string, string | number | boolean | null | undefined>,
              started_at: new Date(),
            });
          } else {
            // Update existing tool run
            newToolRuns.set(toolEvent.tool_run_id, {
              ...existingToolRun,
              status: toolEvent.status,
              details: { ...existingToolRun.details, ...(toolEvent.details || {}) } as Record<string, string | number | boolean | null | undefined>,
              completed_at: toolEvent.status !== "running" ? new Date() : undefined,
            });
          }

          // Retourner une nouvelle session avec la nouvelle Map
          return {
            ...session,
            tool_runs: newToolRuns,
          };
        } else if (event.type === "agent_start" || event.type === "agent_plan") {
          // Créer un nouveau tableau avec le nouvel événement
          return {
            ...session,
            agent_events: [
              ...session.agent_events,
              {
                id: `${currentSessionId}-agent-${Date.now()}`,
                timestamp: new Date(),
                event,
              },
            ],
          };
        }

        return session;
      });
    });
  };

  const handleChatSubmit = async (query: string) => {
    // Create new session ID
    const newSessionId = `session-${Date.now()}`;
    const newSession: TimelineSession = {
      id: newSessionId,
      user_query: query,
      timestamp: new Date(),
      tool_runs: new Map(),
      agent_events: [],
      is_expanded: true, // New session starts expanded
    };

    // CORRECTION: Combiner collapse + ajout de session en un seul setState
    setSessions((prevSessions) => [
      ...prevSessions.map((session) => ({ ...session, is_expanded: false })),
      newSession,
    ]);
    setCurrentSessionId(newSessionId);

    // Reset other state
    setImpactPlan(null);
    setThreadId(null);
    setStatusMessage(null);
    setIsStreaming(true);

    try {
      // Stream events from backend
      for await (const event of streamChatEvents({
        project_id: selectedProject,
        query,
      })) {
        // Log pour debug : tracer tous les événements SSE reçus
        console.log("[SSE Event Received]", event.type, event);

        addEventToCurrentSession(event, newSessionId);

        // Handle special events
        if (event.type === "thread_id") {
          setThreadId(event.thread_id);
        } else if (event.type === "impact_plan_ready") {
          setImpactPlan(event.impact_plan);
          setThreadId(event.thread_id);
          setStatusMessage(t('status.impactPlanReady'));
          break; // Stop streaming when ImpactPlan is ready
        } else if (event.type === "workflow_complete") {
          setStatusMessage(`${t('agentTimeline.workflowComplete')}: ${event.result}`);
        } else if (event.type === "error") {
          setStatusMessage(`${t('status.error')} ${event.error}`);
        }
      }
    } catch (error) {
      console.error("Error streaming events:", error);
      setStatusMessage(
        `${t('status.error')} ${error instanceof Error ? error.message : t('status.error')}`
      );
    } finally {
      setIsStreaming(false);
    }
  };

  // Toggle session expansion
  const handleToggleSession = (sessionId: string) => {
    setSessions((prevSessions) =>
      prevSessions.map((session) =>
        session.id === sessionId
          ? { ...session, is_expanded: !session.is_expanded }
          : session
      )
    );
  };

  const handleApprove = async () => {
    if (!threadId) {
      console.error("No thread ID available");
      return;
    }

    try {
      setStatusMessage(t('status.sendingApproval'));
      const response = await sendApprovalDecision(threadId, true);
      setStatusMessage(`${t('status.approved')} ${response.result}`);
      setImpactPlan(null);
      setThreadId(null);

      // Refresh backlog after approval
      try {
        const items = await getProjectBacklog(selectedProject);
        setBacklogItems(items);
      } catch (error) {
        console.error("Failed to refresh backlog:", error);
      }
    } catch (error) {
      console.error("Error approving plan:", error);
      setStatusMessage(
        `${t('status.errorApproving')} ${error instanceof Error ? error.message : t('status.error')}`
      );
    }
  };

  const handleReject = async () => {
    if (!threadId) {
      console.error("No thread ID available");
      return;
    }

    try {
      setStatusMessage(t('status.sendingRejection'));
      const response = await sendApprovalDecision(threadId, false);
      setStatusMessage(`${t('status.rejected')} ${response.result}`);
      setImpactPlan(null);
      setThreadId(null);
    } catch (error) {
      console.error("Error rejecting plan:", error);
      setStatusMessage(
        `${t('status.errorRejecting')} ${error instanceof Error ? error.message : t('status.error')}`
      );
    }
  };

  const handleCreateProject = async (projectId: string) => {
    try {
      setStatusMessage(t('createProject.creating'));
      await createProject(projectId);

      // Reload projects list
      const projectsList = await getProjects();
      setProjects(projectsList);

      // Select the newly created project
      setSelectedProject(projectId);

      setStatusMessage(t('createProject.success', { name: projectId }));
      setIsCreateProjectModalOpen(false);
    } catch (error) {
      console.error("Error creating project:", error);
      setStatusMessage(
        `${t('status.error')} ${error instanceof Error ? error.message : t('status.error')}`
      );
    }
  };

  const handleDeleteProject = async () => {
    if (!selectedProject) return;

    const projectToDelete = selectedProject;

    try {
      setStatusMessage(t('deleteProject.deleting'));
      await deleteProject(selectedProject);

      // Reload projects list
      const projectsList = await getProjects();
      setProjects(projectsList);

      // Select the first project in the list, or empty string if no projects left
      if (projectsList.length > 0) {
        setSelectedProject(projectsList[0]);
      } else {
        setSelectedProject("");
        setBacklogItems([]);
        setDocuments([]);
        setSessions([]);
      }

      setStatusMessage(t('deleteProject.success', { name: projectToDelete }));
      setIsDeleteProjectModalOpen(false);

      // Clear status message after 3 seconds
      setTimeout(() => {
        setStatusMessage(null);
      }, 3000);
    } catch (error) {
      console.error("Error deleting project:", error);
      setStatusMessage(
        `${t('status.error')} ${error instanceof Error ? error.message : t('status.error')}`
      );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {t('header.title')}
              </h1>
            </div>
            <ProjectSelector
              projects={projects}
              selectedProject={selectedProject}
              onProjectChange={setSelectedProject}
              onCreateProject={() => setIsCreateProjectModalOpen(true)}
              onDeleteProject={() => setIsDeleteProjectModalOpen(true)}
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" style={{ height: 'calc(100vh - 140px)' }}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
          {/* Left Column: Interaction */}
          <div className="flex flex-col space-y-6 h-full overflow-hidden">
            {/* Chat Input */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4">
                {t('newRequest.title')}
              </h2>
              <ChatInput onSubmit={handleChatSubmit} disabled={isStreaming} />
            </div>

            {/* Status Message */}
            {statusMessage && (
              <div
                className={`p-4 rounded-lg ${
                  statusMessage.includes("Erreur")
                    ? "bg-red-100 border border-red-300 text-red-800"
                    : statusMessage.includes("prêt")
                    ? "bg-yellow-100 border border-yellow-300 text-yellow-800"
                    : "bg-green-100 border border-green-300 text-green-800"
                }`}
              >
                <p className="font-semibold">{statusMessage}</p>
              </div>
            )}

            {/* Streaming Indicator */}
            {isStreaming && (
              <div className="bg-blue-100 border border-blue-300 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full" />
                  <p className="text-blue-800 font-semibold">
                    {t('status.processing')}
                  </p>
                </div>
              </div>
            )}

            {/* Timeline View - only show if there are sessions */}
            {sessions.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-6 flex-1 overflow-hidden flex flex-col">
                <TimelineView
                  sessions={sessions}
                  onToggleSession={handleToggleSession}
                />
              </div>
            )}
          </div>

          {/* Right Column: Documents & Backlog */}
          <div className="flex flex-col space-y-6 h-full overflow-hidden">
            {/* Document Manager */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              {isLoadingDocuments ? (
                <div className="flex items-center justify-center py-12">
                  <div className="flex items-center gap-3">
                    <div className="animate-spin h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full" />
                    <p className="text-gray-600">{t('documents.loading')}</p>
                  </div>
                </div>
              ) : (
                <DocumentManager
                  projectId={selectedProject}
                  documents={documents}
                  onUploadSuccess={handleDocumentUploadSuccess}
                />
              )}
            </div>

            {/* Backlog */}
            <div className="bg-white rounded-lg shadow-sm p-6 flex-1 overflow-hidden flex flex-col">
              {isLoadingBacklog ? (
                <div className="flex items-center justify-center py-12">
                  <div className="flex items-center gap-3">
                    <div className="animate-spin h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full" />
                    <p className="text-gray-600">{t('backlog.loading')}</p>
                  </div>
                </div>
              ) : (
                <BacklogView items={backlogItems} />
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Impact Plan Modal */}
      {impactPlan && threadId && (
        <ImpactPlanModal
          impactPlan={impactPlan}
          threadId={threadId}
          onApprove={handleApprove}
          onReject={handleReject}
          isOpen={true}
        />
      )}

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={isCreateProjectModalOpen}
        onClose={() => setIsCreateProjectModalOpen(false)}
        onCreateProject={handleCreateProject}
      />

      {/* Delete Project Modal */}
      <DeleteProjectModal
        isOpen={isDeleteProjectModalOpen}
        onClose={() => setIsDeleteProjectModalOpen(false)}
        onDeleteProject={handleDeleteProject}
        projectName={selectedProject}
      />
    </div>
  );
}
