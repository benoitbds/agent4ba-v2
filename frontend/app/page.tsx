"use client";

import { useState, useEffect } from "react";
import ChatInput from "@/components/ChatInput";
import AgentTimeline from "@/components/AgentTimeline";
import ImpactPlanModal from "@/components/ImpactPlanModal";
import BacklogView from "@/components/BacklogView";
import ProjectSelector from "@/components/ProjectSelector";
import { streamChatEvents, sendApprovalDecision, getProjectBacklog, getProjects } from "@/lib/api";
import type { TimelineEvent, ImpactPlan, SSEEvent, WorkItem } from "@/types/events";

export default function Home() {
  const [projects, setProjects] = useState<string[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [backlogItems, setBacklogItems] = useState<WorkItem[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [impactPlan, setImpactPlan] = useState<ImpactPlan | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isLoadingBacklog, setIsLoadingBacklog] = useState(false);

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

  const addTimelineEvent = (event: SSEEvent) => {
    const timelineEvent: TimelineEvent = {
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
      event,
    };
    setTimelineEvents((prev) => [...prev, timelineEvent]);
  };

  const handleChatSubmit = async (query: string, documentContent?: string) => {
    // Reset state
    setTimelineEvents([]);
    setImpactPlan(null);
    setThreadId(null);
    setStatusMessage(null);
    setIsStreaming(true);

    try {
      // Stream events from backend
      for await (const event of streamChatEvents({
        project_id: selectedProject,
        query,
        document_content: documentContent,
      })) {
        addTimelineEvent(event);

        // Handle special events
        if (event.type === "thread_id") {
          setThreadId(event.thread_id);
        } else if (event.type === "impact_plan_ready") {
          setImpactPlan(event.impact_plan);
          setThreadId(event.thread_id);
          setStatusMessage("ImpactPlan prêt pour validation");
          break; // Stop streaming when ImpactPlan is ready
        } else if (event.type === "workflow_complete") {
          setStatusMessage(`Workflow terminé: ${event.result}`);
        } else if (event.type === "error") {
          setStatusMessage(`Erreur: ${event.error}`);
        }
      }
    } catch (error) {
      console.error("Error streaming events:", error);
      setStatusMessage(
        `Erreur de connexion: ${error instanceof Error ? error.message : "Erreur inconnue"}`
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleApprove = async () => {
    if (!threadId) {
      console.error("No thread ID available");
      return;
    }

    try {
      setStatusMessage("Envoi de l'approbation...");
      const response = await sendApprovalDecision(threadId, true);
      setStatusMessage(`Approuvé: ${response.result}`);
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
        `Erreur lors de l'approbation: ${error instanceof Error ? error.message : "Erreur inconnue"}`
      );
    }
  };

  const handleReject = async () => {
    if (!threadId) {
      console.error("No thread ID available");
      return;
    }

    try {
      setStatusMessage("Envoi du rejet...");
      const response = await sendApprovalDecision(threadId, false);
      setStatusMessage(`Rejeté: ${response.result}`);
      setImpactPlan(null);
      setThreadId(null);
    } catch (error) {
      console.error("Error rejecting plan:", error);
      setStatusMessage(
        `Erreur lors du rejet: ${error instanceof Error ? error.message : "Erreur inconnue"}`
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
                Agent4BA - AI Backlog Assistant
              </h1>
            </div>
            <ProjectSelector
              projects={projects}
              selectedProject={selectedProject}
              onProjectChange={setSelectedProject}
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column: Interaction */}
          <div className="space-y-6">
            {/* Chat Input */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4">
                Nouvelle demande
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
                    Traitement en cours...
                  </p>
                </div>
              </div>
            )}

            {/* Agent Timeline */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <AgentTimeline events={timelineEvents} />
            </div>
          </div>

          {/* Right Column: Backlog and Timeline */}
          <div className="space-y-6">
            {/* Backlog */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <BacklogView items={backlogItems} />
            </div>

            {/* Timeline - only show if there are events */}
            {timelineEvents.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <AgentTimeline events={timelineEvents} />
              </div>
            )}
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
    </div>
  );
}
