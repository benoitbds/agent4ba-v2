"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import ToolRunView from "./ToolRunView";
import type { TimelineSession, SessionTimelineEvent, AgentStartEvent, AgentPlanEvent } from "@/types/events";

interface SessionViewProps {
  session: TimelineSession;
  isLastSession: boolean;
  onToggle: (sessionId: string) => void;
}

export default function SessionView({ session, isLastSession, onToggle }: SessionViewProps) {
  const t = useTranslations();
  const isExpanded = session.is_expanded;

  // Convertir la Map en Array pour l'affichage
  const toolRuns = Array.from(session.tool_runs.values());

  // Extraire les événements agent_start et agent_plan
  const agentStartEvent = session.agent_events.find(
    (e) => e.event.type === "agent_start"
  ) as SessionTimelineEvent | undefined;
  const agentPlanEvent = session.agent_events.find(
    (e) => e.event.type === "agent_plan"
  ) as SessionTimelineEvent | undefined;

  const agentStart = agentStartEvent?.event as AgentStartEvent | undefined;
  const agentPlan = agentPlanEvent?.event as AgentPlanEvent | undefined;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {/* En-tête de la session (cliquable) */}
      <button
        onClick={() => onToggle(session.id)}
        className="w-full px-6 py-4 flex items-center gap-4 hover:bg-gray-50 transition-colors text-left"
      >
        {/* Chevron */}
        <span className="text-gray-600 text-lg flex-shrink-0">
          {isExpanded ? "▼" : "▶"}
        </span>

        {/* Icône utilisateur */}
        <span className="text-2xl flex-shrink-0">👤</span>

        {/* Requête utilisateur */}
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-900 text-base">{t("timeline.userRequest")}</p>
          <p className="text-sm text-gray-700 mt-1 italic line-clamp-2">
            &quot;{session.user_query}&quot;
          </p>
        </div>

        {/* Badge avec nombre d'outils */}
        <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">
          {toolRuns.length} {t("timeline.toolsUsed")}
        </span>

        {/* Timestamp */}
        <span className="text-xs text-gray-400">
          {session.timestamp.toLocaleTimeString()}
        </span>
      </button>

      {/* Contenu dépliable */}
      {isExpanded && (
        <div className="border-t border-gray-100 bg-gray-50/50">
          <div className="px-6 py-4 space-y-4">
            {/* Reformulation de l'agent (agent_start) */}
            {agentStart && (
              <div className="bg-white border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <span className="text-2xl flex-shrink-0">🤖</span>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900 mb-2">
                      {agentStart.agent_name}
                    </p>
                    <div className="bg-blue-50 border-l-4 border-blue-400 p-3 rounded">
                      <p className="text-sm text-gray-700 italic">
                        &quot;{agentStart.thought}&quot;
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Plan d'action de l'agent (agent_plan) */}
            {agentPlan && (
              <div className="bg-white border border-cyan-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <span className="text-2xl flex-shrink-0">📋</span>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900 mb-3">
                      {t("timeline.actionPlan")} - {agentPlan.agent_name}
                    </p>
                    <ul className="space-y-2">
                      {agentPlan.steps.map((step, index) => (
                        <li key={index} className="flex items-start gap-2 text-sm">
                          <span className="text-blue-500 font-bold flex-shrink-0 mt-0.5">
                            {index + 1}.
                          </span>
                          <span className="text-gray-700">{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Liste des outils utilisés */}
            {toolRuns.length > 0 && (
              <div className="space-y-3">
                <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  {t("timeline.toolsUsed")}
                </h5>
                <div className="space-y-3">
                  {toolRuns.map((toolRun) => (
                    <ToolRunView key={toolRun.tool_run_id} toolRun={toolRun} />
                  ))}
                </div>
              </div>
            )}

            {/* Message si aucun outil n'a été utilisé */}
            {toolRuns.length === 0 && !agentStart && !agentPlan && (
              <p className="text-sm text-gray-500 italic text-center py-4">
                {t("timeline.noToolsUsed")}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
