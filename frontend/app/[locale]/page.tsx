"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from 'next-intl';
import ChatInput, { ChatInputRef } from "@/components/ChatInput";
import TimelineView from "@/components/TimelineView";
import TimelineDisplay from "@/components/TimelineDisplay";
import ImpactPlanModal from "@/components/ImpactPlanModal";
import CreateProjectModal from "@/components/CreateProjectModal";
import DeleteProjectModal from "@/components/DeleteProjectModal";
import BacklogView from "@/components/BacklogView";
import DocumentManagementModal from "@/components/DocumentManagementModal";
import { ProjectUsersModal } from "@/components/ProjectUsersModal";
import ContextPills from "@/components/ContextPills";
import { PrivateRoute } from "@/components/PrivateRoute";
import { Header } from "@/components/Header";
import { useAuth } from "@/context/AuthContext";
import { useTimelineStream } from "@/hooks/useTimelineStream";
import { streamChatEvents, sendApprovalDecision, getProjectBacklog, getProjects, getProjectDocuments, getProjectTimelineHistory, createProject, deleteProject, UnauthorizedError, executeWorkflow, respondToClarification } from "@/lib/api";
import type { TimelineSession, ToolRunState, ImpactPlan, SSEEvent, WorkItem, ToolUsedEvent, TimelineEvent, ContextItem, ClarificationNeededResponse, ApprovalNeededResponse } from "@/types/events";

export default function Home() {
  const t = useTranslations();
  const router = useRouter();
  const { logout, token } = useAuth();
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
  const [statusType, setStatusType] = useState<'error' | 'warning' | 'success' | 'info' | null>(null);
  const [isLoadingBacklog, setIsLoadingBacklog] = useState(false);
  const [isCreateProjectModalOpen, setIsCreateProjectModalOpen] = useState(false);
  const [isDeleteProjectModalOpen, setIsDeleteProjectModalOpen] = useState(false);
  const [isDocumentModalOpen, setIsDocumentModalOpen] = useState(false);
  const [isUsersModalOpen, setIsUsersModalOpen] = useState(false);
  const [chatContext, setChatContext] = useState<ContextItem[]>([]);
  const chatInputRef = useRef<ChatInputRef>(null);

  // Multi-turn conversation state
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [clarificationQuestion, setClarificationQuestion] = useState<string | null>(null);
  const [inputPlaceholder, setInputPlaceholder] = useState<string>(t('newRequest.placeholder'));

  // Real-time timeline SSE state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const { events: timelineEvents, isConnected, updateEvent } = useTimelineStream(sessionId, token);

  // Helper function to handle 401 errors - use useCallback to memoize
  const handleUnauthorizedError = useCallback((error: unknown) => {
    if (error instanceof UnauthorizedError) {
      // Clear auth context and redirect to login
      logout();
      router.push("/login");
      return true;
    }
    return false;
  }, [logout, router]);

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
        if (handleUnauthorizedError(error)) return;
        console.error("Error loading projects:", error);
      }
    };

    loadProjects();
  }, [handleUnauthorizedError]);

  // Load backlog when selected project changes
  useEffect(() => {
    if (!selectedProject) return;

    const loadBacklog = async () => {
      setIsLoadingBacklog(true);
      try {
        const items = await getProjectBacklog(selectedProject);
        setBacklogItems(items);
      } catch (error) {
        if (handleUnauthorizedError(error)) return;
        console.error("Error loading backlog:", error);
        setBacklogItems([]);
      } finally {
        setIsLoadingBacklog(false);
      }
    };

    loadBacklog();
  }, [selectedProject, handleUnauthorizedError]);

  // Load documents when selected project changes
  useEffect(() => {
    if (!selectedProject) return;

    const loadDocuments = async () => {
      try {
        const docs = await getProjectDocuments(selectedProject);
        setDocuments(docs);
      } catch (error) {
        if (handleUnauthorizedError(error)) return;
        console.error("Error loading documents:", error);
        setDocuments([]);
      }
    };

    loadDocuments();
  }, [selectedProject, handleUnauthorizedError]);

  // Reset context and conversation state when project changes
  useEffect(() => {
    setChatContext([]);
    setConversationId(null);
    setClarificationQuestion(null);
    setInputPlaceholder(t('newRequest.placeholder'));
  }, [selectedProject, t]);

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
        if (handleUnauthorizedError(error)) return;
        console.error("Error loading timeline history:", error);
        // En cas d'erreur, réinitialiser la timeline à vide
        setSessions([]);
      }
    };

    loadTimelineHistory();
  }, [selectedProject, handleUnauthorizedError, t]);

  // Function to refresh documents list after upload
  const handleDocumentUploadSuccess = async () => {
    try {
      const docs = await getProjectDocuments(selectedProject);
      setDocuments(docs);
    } catch (error) {
      if (handleUnauthorizedError(error)) return;
      console.error("Error refreshing documents:", error);
    }
  };

  // Function to add a document to the chat context
  const handleSelectDocument = (documentName: string) => {
    // Check if document is already in context
    if (chatContext.some((item) => item.type === "document" && item.id === documentName)) {
      return;
    }

    setChatContext((prev) => [
      ...prev,
      {
        type: "document",
        id: documentName,
        name: documentName,
      },
    ]);
  };

  // Function to add a work item to the chat context
  const handleSelectWorkItem = (workItem: WorkItem) => {
    // Check if work item is already in context
    if (chatContext.some((item) => item.type === "work_item" && item.id === workItem.id)) {
      return;
    }

    setChatContext((prev) => [
      ...prev,
      {
        type: "work_item",
        id: workItem.id,
        name: workItem.title,
      },
    ]);
  };

  // Function to remove an item from the chat context
  const handleRemoveFromContext = (id: string) => {
    setChatContext((prev) => prev.filter((item) => item.id !== id));
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
    // Déterminer si c'est une nouvelle requête ou une réponse à une clarification
    const isRespondingToClarification = conversationId !== null && clarificationQuestion !== null;

    setIsStreaming(true);
    setStatusMessage(null);
    setStatusType(null);

    try {
      if (isRespondingToClarification) {
        // Cas 1: Réponse à une clarification
        console.log("[MULTI-TURN] Responding to clarification:", conversationId);

        const response = await respondToClarification(conversationId, query);

        // Réinitialiser l'état de conversation
        setConversationId(null);
        setClarificationQuestion(null);
        setInputPlaceholder(t('newRequest.placeholder'));

        // Afficher le résultat final
        setStatusMessage(`${t('agentTimeline.workflowComplete')}: ${response.result}`);
        setStatusType('success');

        // Rafraîchir le backlog après la complétion
        try {
          const items = await getProjectBacklog(selectedProject);
          setBacklogItems(items);
        } catch (error) {
          if (handleUnauthorizedError(error)) return;
          console.error("Failed to refresh backlog:", error);
        }
      } else {
        // Cas 2: Nouvelle requête
        console.log("[MULTI-TURN] Starting new request");

        // Générer un session_id AVANT d'appeler /execute pour le streaming temps réel
        const newSessionId = crypto.randomUUID();
        console.log("[TIMELINE] Generated session_id for real-time streaming:", newSessionId);

        // Ouvrir immédiatement la connexion SSE AVANT l'exécution du workflow
        setSessionId(newSessionId);

        const response = await executeWorkflow({
          project_id: selectedProject,
          query,
          context: chatContext.length > 0 ? chatContext : undefined,
          session_id: newSessionId, // Passer le session_id au backend
        });

        // Le backend retourne toujours 202 Accepted avec le session_id
        // Les événements (workflow complete, approval needed, etc.) arrivent via SSE
        console.log("[EXECUTE] Workflow started with session_id:", response.session_id);

        // La suite de la logique est gérée par le useEffect qui écoute timelineEvents
      }
    } catch (error) {
      if (handleUnauthorizedError(error)) return;
      console.error("Error executing workflow:", error);
      setStatusMessage(
        `${t('status.error')} ${error instanceof Error ? error.message : t('status.error')}`
      );
      setStatusType('error');

      // En cas d'erreur, réinitialiser l'état de conversation
      setConversationId(null);
      setClarificationQuestion(null);
      setInputPlaceholder(t('newRequest.placeholder'));
    } finally {
      setIsStreaming(false);
      // Clear context after sending the request (only for new requests)
      if (!isRespondingToClarification) {
        setChatContext([]);
      }
    }
  };

  // useEffect pour écouter les événements de timeline et réagir aux événements spéciaux
  useEffect(() => {
    if (timelineEvents.length === 0) return;

    // Récupérer le dernier événement
    const lastEvent = timelineEvents[timelineEvents.length - 1];

    if (lastEvent.type === 'WORKFLOW_COMPLETE') {
      console.log("[TIMELINE] Workflow completed");
      setStatusMessage(lastEvent.message);
      setStatusType('success');

      // Rafraîchir le backlog après la complétion
      if (selectedProject) {
        getProjectBacklog(selectedProject)
          .then((items) => setBacklogItems(items))
          .catch((error) => {
            if (handleUnauthorizedError(error)) return;
            console.error("Failed to refresh backlog:", error);
          });

        // Rafraîchir la timeline après la complétion
        getProjectTimelineHistory(selectedProject)
          .then((history) => {
            const historySessions: TimelineSession[] = history.map((historySession, index) => {
              const sessionTimestamp = new Date(historySession.timestamp);
              const sessionId = `history-${sessionTimestamp.getTime()}-${index}`;
              const userRequestEvent = historySession.events.find((evt: SSEEvent) => evt.type === "user_request");
              const userQuery = userRequestEvent && "query" in userRequestEvent ? userRequestEvent.query : t('agentTimeline.historicalSession');
              const toolRunsMap = new Map<string, ToolRunState>();
              const agentEvents: TimelineEvent[] = [];

              historySession.events.forEach((evt: SSEEvent, eventIndex: number) => {
                if (evt.type === "tool_used") {
                  const toolEvent = evt as ToolUsedEvent;
                  const existingToolRun = toolRunsMap.get(toolEvent.tool_run_id);
                  if (!existingToolRun) {
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
                is_expanded: false,
              };
            });
            setSessions(historySessions);
          })
          .catch((error) => {
            if (handleUnauthorizedError(error)) return;
            console.error("Failed to refresh timeline:", error);
          });
      }
    } else if (lastEvent.type === 'IMPACT_PLAN_READY' && lastEvent.status === 'WAITING') {
      console.log("[TIMELINE] Impact plan ready for approval");

      // Extraire les détails de l'impact plan depuis l'événement
      // Ne traiter cet événement que si le statut est WAITING (pas encore approuvé)
      if (lastEvent.details && lastEvent.details.impact_plan && lastEvent.details.thread_id) {
        setThreadId(lastEvent.details.thread_id as string);
        setImpactPlan(lastEvent.details.impact_plan as ImpactPlan);
        setStatusMessage(t('status.approvalRequired') || "Approval required for the ImpactPlan");
        setStatusType('info');
      }
    } else if (lastEvent.type === 'CLARIFICATION_NEEDED') {
      console.log("[TIMELINE] Clarification needed:", lastEvent.message);

      // Utiliser le session_id actuel comme conversation_id pour la clarification
      setConversationId(sessionId);
      setClarificationQuestion(lastEvent.message);
      setInputPlaceholder(t('newRequest.clarificationPlaceholder') || "Entrez votre réponse...");
      setStatusMessage(lastEvent.message);
      setStatusType('warning');
    }
  }, [timelineEvents, selectedProject, sessionId, t, handleUnauthorizedError]);

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
      setStatusType('info');
      const response = await sendApprovalDecision(threadId, true);
      setStatusMessage(`${t('status.approved')} ${response.result}`);
      setStatusType('success');

      // Mettre à jour le statut de l'événement IMPACT_PLAN_READY dans la timeline
      const impactPlanEvent = timelineEvents.find(event => event.type === 'IMPACT_PLAN_READY' && event.status === 'WAITING');
      if (impactPlanEvent) {
        console.log('[IMPACT_PLAN] Updating event status to SUCCESS:', impactPlanEvent.event_id);
        updateEvent(impactPlanEvent.event_id, { status: 'SUCCESS' });
      }

      // Fermer la modale immédiatement après la confirmation
      setImpactPlan(null);
      setThreadId(null);

      // Refresh backlog et timeline en arrière-plan (sans bloquer la fermeture de la modale)
      Promise.all([
        getProjectBacklog(selectedProject).then((items) => setBacklogItems(items)),
        getProjectTimelineHistory(selectedProject).then((history) => {
          const historySessions: TimelineSession[] = history.map((historySession, index) => {
            const sessionTimestamp = new Date(historySession.timestamp);
            const sessionId = `history-${sessionTimestamp.getTime()}-${index}`;
            const userRequestEvent = historySession.events.find((evt: SSEEvent) => evt.type === "user_request");
            const userQuery = userRequestEvent && "query" in userRequestEvent ? userRequestEvent.query : t('agentTimeline.historicalSession');
            const toolRunsMap = new Map<string, ToolRunState>();
            const agentEvents: TimelineEvent[] = [];

            historySession.events.forEach((evt: SSEEvent, eventIndex: number) => {
              if (evt.type === "tool_used") {
                const toolEvent = evt as ToolUsedEvent;
                const existingToolRun = toolRunsMap.get(toolEvent.tool_run_id);
                if (!existingToolRun) {
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
              is_expanded: false,
            };
          });
          setSessions(historySessions);
        })
      ]).catch((error) => {
        if (handleUnauthorizedError(error)) return;
        console.error("Failed to refresh data after approval:", error);
      });
    } catch (error) {
      if (handleUnauthorizedError(error)) return;
      console.error("Error approving plan:", error);
      setStatusMessage(
        `${t('status.errorApproving')} ${error instanceof Error ? error.message : t('status.error')}`
      );
      setStatusType('error');
    }
  };

  const handleReject = async () => {
    if (!threadId) {
      console.error("No thread ID available");
      return;
    }

    try {
      setStatusMessage(t('status.sendingRejection'));
      setStatusType('info');
      const response = await sendApprovalDecision(threadId, false);
      setStatusMessage(`${t('status.rejected')} ${response.result}`);
      setStatusType('success');
      setImpactPlan(null);
      setThreadId(null);
    } catch (error) {
      if (handleUnauthorizedError(error)) return;
      console.error("Error rejecting plan:", error);
      setStatusMessage(
        `${t('status.errorRejecting')} ${error instanceof Error ? error.message : t('status.error')}`
      );
      setStatusType('error');
    }
  };

  const handleCreateProject = async (projectId: string) => {
    try {
      setStatusMessage(t('createProject.creating'));
      setStatusType('info');
      await createProject(projectId);

      // Reload projects list
      const projectsList = await getProjects();
      setProjects(projectsList);

      // Select the newly created project
      setSelectedProject(projectId);

      setStatusMessage(t('createProject.success', { name: projectId }));
      setStatusType('success');
      setIsCreateProjectModalOpen(false);

      // Focus on chat input after modal closes
      setTimeout(() => {
        chatInputRef.current?.focus();
      }, 100);
    } catch (error) {
      if (handleUnauthorizedError(error)) return;
      console.error("Error creating project:", error);
      setStatusMessage(
        `${t('status.error')} ${error instanceof Error ? error.message : t('status.error')}`
      );
      setStatusType('error');
    }
  };

  const handleDeleteProject = async () => {
    if (!selectedProject) return;

    const projectToDelete = selectedProject;

    try {
      setStatusMessage(t('deleteProject.deleting'));
      setStatusType('info');
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
      setStatusType('success');
      setIsDeleteProjectModalOpen(false);

      // Clear status message after 3 seconds
      setTimeout(() => {
        setStatusMessage(null);
        setStatusType(null);
      }, 3000);
    } catch (error) {
      if (handleUnauthorizedError(error)) return;
      console.error("Error deleting project:", error);
      setStatusMessage(
        `${t('status.error')} ${error instanceof Error ? error.message : t('status.error')}`
      );
      setStatusType('error');
    }
  };

  return (
    <PrivateRoute>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <Header
          projects={projects}
          selectedProject={selectedProject}
          onProjectChange={setSelectedProject}
          onOpenDocuments={() => setIsDocumentModalOpen(true)}
          onCreateProject={() => setIsCreateProjectModalOpen(true)}
          onDeleteProject={() => setIsDeleteProjectModalOpen(true)}
          onManageUsers={() => setIsUsersModalOpen(true)}
        />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" style={{ height: 'calc(100vh - 80px)' }}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
          {/* Left Column: Interaction */}
          <div className="flex flex-col space-y-6 h-full overflow-hidden">
            {/* Chat Input */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4">
                {t('newRequest.title')}
              </h2>
              <ChatInput
                ref={chatInputRef}
                onSubmit={handleChatSubmit}
                disabled={isStreaming}
                placeholder={inputPlaceholder}
              />
              <ContextPills context={chatContext} onRemove={handleRemoveFromContext} />
            </div>

            {/* Status Message */}
            {statusMessage && (
              <div
                className={`p-4 rounded-lg ${
                  statusType === "error"
                    ? "bg-red-100 border border-red-300 text-red-800"
                    : statusType === "warning"
                    ? "bg-yellow-100 border border-yellow-300 text-yellow-800"
                    : statusType === "info"
                    ? "bg-blue-100 border border-blue-300 text-blue-800"
                    : "bg-green-100 border border-green-300 text-green-800"
                }`}
              >
                {clarificationQuestion && (
                  <div className="flex items-start gap-2 mb-2">
                    <span className="text-2xl">❓</span>
                    <p className="font-semibold flex-1">{t('newRequest.clarificationNeeded')}</p>
                  </div>
                )}
                <p className={clarificationQuestion ? "" : "font-semibold"}>{statusMessage}</p>
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

            {/* Real-time SSE Timeline - only show if session is active or events exist */}
            {(sessionId || timelineEvents.length > 0) && (
              <div className="bg-white rounded-lg shadow-sm p-6 flex-1 overflow-hidden flex flex-col">
                <TimelineDisplay events={timelineEvents} />
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

          {/* Right Column: Backlog */}
          <div className="flex flex-col h-full overflow-hidden">
            {/* Backlog */}
            <div className="bg-white rounded-lg shadow-sm p-6 h-full overflow-hidden flex flex-col">
              {isLoadingBacklog ? (
                <div className="flex items-center justify-center py-12">
                  <div className="flex items-center gap-3">
                    <div className="animate-spin h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full" />
                    <p className="text-gray-600">{t('backlog.loading')}</p>
                  </div>
                </div>
              ) : (
                <BacklogView
                  items={backlogItems}
                  projectId={selectedProject}
                  onSelectItem={handleSelectWorkItem}
                  onItemUpdated={async () => {
                    // Rafraîchir le backlog après une mise à jour
                    try {
                      const items = await getProjectBacklog(selectedProject);
                      setBacklogItems(items);
                    } catch (error) {
                      if (handleUnauthorizedError(error)) return;
                      console.error("Error refreshing backlog after update:", error);
                    }
                  }}
                />
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

      {/* Document Management Modal */}
      <DocumentManagementModal
        isOpen={isDocumentModalOpen}
        onClose={() => setIsDocumentModalOpen(false)}
        projectId={selectedProject}
        documents={documents}
        onDocumentsChange={handleDocumentUploadSuccess}
        onSelectDocument={handleSelectDocument}
      />

      {/* Project Users Modal */}
      <ProjectUsersModal
        isOpen={isUsersModalOpen}
        onClose={() => setIsUsersModalOpen(false)}
        projectId={selectedProject}
      />
      </div>
    </PrivateRoute>
  );
}
