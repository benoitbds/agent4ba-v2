"use client";

import { useState, useMemo } from "react";
import type { TimelineEvent } from "@/types/events";

interface AgentTimelineProps {
  events: TimelineEvent[];
}

export default function AgentTimeline({ events }: AgentTimelineProps) {
  // État pour gérer l'ouverture/fermeture des accordéons
  const [openItems, setOpenItems] = useState<Set<string>>(new Set());

  // État pour suivre les étapes du plan complétées
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <p>En attente d&apos;événements...</p>
      </div>
    );
  }

  const toggleItem = (itemId: string) => {
    setOpenItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  // Extraire le plan d'action et suivre la progression
  const agentPlan = useMemo(() => {
    const planEvent = events.find((e) => e.event.type === "agent_plan");
    if (planEvent && "steps" in planEvent.event) {
      return planEvent.event.steps;
    }
    return null;
  }, [events]);

  // Calculer les étapes complétées basées sur les outils utilisés
  useMemo(() => {
    if (!agentPlan) return;

    const toolEvents = events.filter((e) => e.event.type === "tool_used");
    const completedToolsCount = toolEvents.filter(
      (e) => "status" in e.event && e.event.status === "completed"
    ).length;

    // Marquer les étapes comme complétées au fur et à mesure
    const newCompleted = new Set<number>();
    for (let i = 0; i < Math.min(completedToolsCount, agentPlan.length); i++) {
      newCompleted.add(i);
    }
    setCompletedSteps(newCompleted);
  }, [events, agentPlan]);

  const renderEvent = (event: TimelineEvent) => {
    const { type } = event.event;

    // Session initialisée
    if (type === "thread_id" && "thread_id" in event.event) {
      return (
        <div
          key={event.id}
          className="bg-white border-l-4 border-l-purple-400 rounded-lg p-5 shadow-sm"
        >
          <div className="flex items-start gap-4">
            <span className="text-2xl">🔗</span>
            <div className="flex-1">
              <p className="font-semibold text-gray-900 text-lg">
                Session initialisée
              </p>
              <p className="text-sm text-gray-500 font-mono mt-1">
                Thread: {event.event.thread_id}
              </p>
            </div>
          </div>
        </div>
      );
    }

    // Reformulation de l'agent (AgentStart)
    if (type === "agent_start" && "thought" in event.event) {
      return (
        <div
          key={event.id}
          className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-l-blue-500 rounded-lg p-6 shadow-md"
        >
          <div className="flex items-start gap-4">
            <span className="text-3xl">🤖</span>
            <div className="flex-1">
              <p className="font-semibold text-blue-900 text-lg mb-2">
                {event.event.agent_name}
              </p>
              <p className="text-gray-800 text-base leading-relaxed">
                {event.event.thought}
              </p>
            </div>
          </div>
        </div>
      );
    }

    // Plan d'action (AgentPlan)
    if (type === "agent_plan" && "steps" in event.event) {
      return (
        <div
          key={event.id}
          className="bg-white border-l-4 border-l-amber-400 rounded-lg p-6 shadow-sm"
        >
          <div className="flex items-start gap-4">
            <span className="text-3xl">📋</span>
            <div className="flex-1">
              <p className="font-semibold text-gray-900 text-lg mb-4">
                Plan d&apos;action
              </p>
              <ul className="space-y-2">
                {event.event.steps.map((step: string, index: number) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="text-xl flex-shrink-0 mt-0.5">
                      {completedSteps.has(index) ? "✅" : "⬜"}
                    </span>
                    <span
                      className={`${
                        completedSteps.has(index)
                          ? "text-gray-900 font-medium"
                          : "text-gray-600"
                      }`}
                    >
                      {step}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      );
    }

    // Outil utilisé (ToolUsed)
    if (type === "tool_used" && "tool_name" in event.event) {
      const isOpen = openItems.has(event.id);
      const statusColor =
        event.event.status === "completed"
          ? "border-l-green-400"
          : event.event.status === "error"
          ? "border-l-red-400"
          : "border-l-blue-400";

      const statusIcon =
        event.event.status === "completed"
          ? "✓"
          : event.event.status === "error"
          ? "⚠"
          : "⏳";

      return (
        <div
          key={event.id}
          className={`bg-white border border-gray-200 ${statusColor} border-l-4 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow`}
        >
          {/* Header cliquable */}
          <button
            onClick={() => toggleItem(event.id)}
            className="w-full px-5 py-4 flex items-center gap-4 hover:bg-gray-50 transition-colors text-left"
          >
            {/* Chevron */}
            <span className="text-gray-500 text-sm flex-shrink-0">
              {isOpen ? "▼" : "▶"}
            </span>

            {/* Icône de l'outil */}
            <span className="text-2xl flex-shrink-0">
              {event.event.tool_icon}
            </span>

            {/* Nom et description */}
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-gray-900">
                {event.event.tool_name}
              </p>
              <p className="text-sm text-gray-600 mt-0.5">
                {event.event.description}
              </p>
            </div>

            {/* Badge de statut */}
            <span className="text-xl flex-shrink-0">{statusIcon}</span>
          </button>

          {/* Contenu dépliable (détails) */}
          {isOpen && event.event.details && (
            <div className="border-t border-gray-100 bg-gray-50 px-5 py-4">
              <p className="text-xs font-medium text-gray-700 mb-2">
                Détails :
              </p>
              <pre className="text-xs text-gray-700 bg-white border border-gray-200 rounded p-3 overflow-x-auto">
                {JSON.stringify(event.event.details, null, 2)}
              </pre>
            </div>
          )}
        </div>
      );
    }

    // ImpactPlan prêt
    if (type === "impact_plan_ready" && "impact_plan" in event.event) {
      return (
        <div
          key={event.id}
          className="bg-white border-l-4 border-l-yellow-400 rounded-lg p-5 shadow-sm"
        >
          <div className="flex items-start gap-4">
            <span className="text-2xl">📄</span>
            <div className="flex-1">
              <p className="font-semibold text-gray-900 text-lg">
                ImpactPlan prêt pour validation
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {event.event.impact_plan.new_items.length} nouveaux items
              </p>
            </div>
          </div>
        </div>
      );
    }

    // Workflow terminé
    if (type === "workflow_complete" && "result" in event.event) {
      return (
        <div
          key={event.id}
          className="bg-white border-l-4 border-l-emerald-400 rounded-lg p-5 shadow-sm"
        >
          <div className="flex items-start gap-4">
            <span className="text-2xl">🏁</span>
            <div className="flex-1">
              <p className="font-semibold text-gray-900 text-lg">
                Workflow terminé
              </p>
              <p className="text-sm text-gray-700 mt-1">
                {event.event.result}
              </p>
            </div>
          </div>
        </div>
      );
    }

    // Erreur
    if (type === "error" && "error" in event.event) {
      return (
        <div
          key={event.id}
          className="bg-white border-l-4 border-l-red-500 rounded-lg p-5 shadow-sm"
        >
          <div className="flex items-start gap-4">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <p className="font-semibold text-red-900 text-lg">Erreur</p>
              <p className="text-sm text-red-700 mt-1">{event.event.error}</p>
              {event.event.details && (
                <p className="text-xs text-gray-600 mt-1">
                  {event.event.details}
                </p>
              )}
            </div>
          </div>
        </div>
      );
    }

    // Événements ignorés (node_start, node_end, llm_start, llm_end, etc.)
    // On ne les affiche plus dans le nouveau design narratif
    return null;
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        Timeline d&apos;exécution
      </h2>

      {/* Affichage chronologique (plus ancien en haut, plus récent en bas) */}
      <div className="flex flex-col space-y-4">
        {events.map((event) => renderEvent(event))}
      </div>
    </div>
  );
}
