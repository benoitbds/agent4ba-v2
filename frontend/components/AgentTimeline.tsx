"use client";

import { useRef, useEffect } from "react";
import { Link2, Brain, MessageSquare, FileText, Flag } from "lucide-react";
import type { TimelineEvent } from "@/types/events";

interface AgentTimelineProps {
  events: TimelineEvent[];
}

export default function AgentTimeline({ events }: AgentTimelineProps) {
  // Référence pour le scroll automatique
  const timelineEndRef = useRef<HTMLDivElement | null>(null);

  // Fonction pour scroller vers le bas
  const scrollToBottom = () => {
    timelineEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Effet pour scroller automatiquement quand les événements changent
  useEffect(() => {
    scrollToBottom();
  }, [events]);

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <p>En attente d&apos;événements...</p>
      </div>
    );
  }

  // Simplification : afficher chaque événement individuellement pour une timeline narrative claire
  // Les événements node_start et node_end sont optionnels et traités comme les autres
  const shouldDisplayEvent = (type: string): boolean => {
    // Filtrer les événements de bas niveau qu'on ne veut pas afficher
    return type !== "llm_token"; // Les tokens individuels sont trop verbeux
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case "thread_id":
        return <Link2 className="w-5 h-5" />;
      case "user_request":
        return "👤";
      case "agent_start":
        return "🤖";
      case "agent_plan":
        return "📋";
      case "tool_used":
        return "🔧";
      case "node_start":
        return "▶";
      case "node_end":
        return "✓";
      case "llm_start":
        return <Brain className="w-5 h-5" />;
      case "llm_token":
        return <MessageSquare className="w-5 h-5" />;
      case "llm_end":
        return "✓";
      case "impact_plan_ready":
        return "🟡";
      case "workflow_complete":
        return <Flag className="w-5 h-5" />;
      case "error":
        return "⚠";
      default:
        return "•";
    }
  };

  // Nouvelle fonction pour obtenir la couleur de bordure gauche (design clair)
  const getBorderColor = (status?: string, type?: string) => {
    if (status === "error" || type === "error") return "border-l-red-400";
    if (status === "completed") return "border-l-green-400";
    if (status === "running") return "border-l-blue-400";
    if (type === "agent_start") return "border-l-blue-500";
    if (type === "agent_plan") return "border-l-cyan-400";
    if (type === "tool_used") return "border-l-orange-400";
    if (type === "impact_plan_ready") return "border-l-amber-400";
    if (type === "workflow_complete") return "border-l-emerald-400";
    if (type === "thread_id") return "border-l-purple-400";
    if (type === "user_request") return "border-l-indigo-400";
    return "border-l-gray-300";
  };

  const formatEventDetails = (event: TimelineEvent, compact = false) => {
    const { type } = event.event;

    switch (type) {
      case "thread_id":
        return (
          <div>
            <p className="font-semibold text-gray-900">Session initialisée</p>
            {!compact && (
              <p className="text-sm text-gray-500 font-mono truncate mt-1">
                Thread: {event.event.thread_id}
              </p>
            )}
          </div>
        );
      case "user_request":
        return (
          <div>
            <p className="font-semibold text-gray-900">Requête utilisateur</p>
            <p className="text-sm text-gray-700 mt-2 italic">
              &quot;{event.event.query}&quot;
            </p>
          </div>
        );
      case "agent_start":
        return (
          <div>
            <p className="font-semibold text-gray-900 mb-2">
              🤖 {event.event.agent_name}
            </p>
            <div className="bg-blue-50 border-l-4 border-blue-400 p-3 rounded">
              <p className="text-sm text-gray-700 italic">
                &quot;{event.event.thought}&quot;
              </p>
            </div>
          </div>
        );
      case "agent_plan":
        return (
          <div>
            <p className="font-semibold text-gray-900 mb-3">
              📋 Plan d&apos;action - {event.event.agent_name}
            </p>
            <ul className="space-y-2">
              {event.event.steps.map((step, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <span className="text-blue-500 font-bold flex-shrink-0 mt-0.5">
                    {index + 1}.
                  </span>
                  <span className="text-gray-700">{step}</span>
                </li>
              ))}
            </ul>
          </div>
        );
      case "tool_used":
        return (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{event.event.tool_icon}</span>
              <div className="flex-1">
                <p className="font-semibold text-gray-900">
                  {event.event.tool_name}
                </p>
                <p className="text-xs text-gray-500">{event.event.description}</p>
              </div>
              <span
                className={`text-xs font-medium px-2 py-1 rounded ${
                  event.event.status === "completed"
                    ? "bg-green-100 text-green-700"
                    : event.event.status === "error"
                    ? "bg-red-100 text-red-700"
                    : "bg-blue-100 text-blue-700"
                }`}
              >
                {event.event.status === "completed"
                  ? "✓ Terminé"
                  : event.event.status === "error"
                  ? "⚠ Erreur"
                  : "⏳ En cours"}
              </span>
            </div>
            {!compact && event.event.details && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-gray-600 hover:text-gray-900 font-medium">
                  Voir les détails
                </summary>
                <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded text-xs overflow-x-auto">
                  {JSON.stringify(event.event.details, null, 2)}
                </pre>
              </details>
            )}
          </div>
        );
      case "node_start":
        return (
          <div>
            <p className="text-sm text-gray-900">Démarré</p>
            {!compact && (
              <p className="text-xs text-gray-500 mt-1">
                {event.timestamp.toLocaleTimeString()}
              </p>
            )}
          </div>
        );
      case "node_end":
        return (
          <div>
            <p className="text-sm text-gray-900">Terminé</p>
            {!compact && event.event.output && (
              <details className="mt-2 text-xs">
                <summary className="cursor-pointer text-gray-600 hover:text-gray-900 font-medium">
                  Voir la sortie
                </summary>
                <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded text-xs overflow-x-auto">
                  {JSON.stringify(event.event.output, null, 2)}
                </pre>
              </details>
            )}
            {!compact && (
              <p className="text-xs text-gray-500 mt-1">
                {event.timestamp.toLocaleTimeString()}
              </p>
            )}
          </div>
        );
      case "llm_start":
        return (
          <div>
            <p className="text-sm text-gray-700">LLM démarré</p>
            {!compact && "model" in event.event && event.event.model && (
              <p className="text-xs text-gray-500 mt-1">
                Modèle: {event.event.model}
              </p>
            )}
          </div>
        );
      case "llm_end":
        return (
          <div>
            <p className="text-sm text-gray-700">LLM terminé</p>
            {!compact && "content" in event.event && event.event.content && (
              <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                {event.event.content}
              </p>
            )}
          </div>
        );
      case "llm_token":
        return (
          <div>
            <p className="text-xs text-gray-600">Token: {event.event.token}</p>
          </div>
        );
      case "impact_plan_ready":
        return (
          <div>
            <p className="font-semibold text-gray-900">
              ImpactPlan prêt pour validation
            </p>
            {!compact && (
              <p className="text-sm text-gray-600 mt-1">
                {event.event.impact_plan.new_items.length} nouveaux items
              </p>
            )}
          </div>
        );
      case "workflow_complete":
        return (
          <div>
            <p className="font-semibold text-gray-900">Workflow terminé</p>
            {!compact && (
              <p className="text-sm text-gray-600 mt-1">{event.event.result}</p>
            )}
          </div>
        );
      case "error":
        return (
          <div>
            <p className="font-semibold text-red-700">Erreur</p>
            <p className="text-sm text-gray-700 mt-1">{event.event.error}</p>
            {!compact && event.event.details && (
              <p className="text-xs text-gray-600 mt-1">{event.event.details}</p>
            )}
          </div>
        );
      default:
        return (
          <div>
            <p className="font-medium text-gray-900">{type}</p>
          </div>
        );
    }
  };

  // Filtrer les événements à afficher
  const filteredEvents = events.filter((event) =>
    shouldDisplayEvent(event.event.type)
  );

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">
        Timeline d&apos;exécution
      </h2>

      <div className="space-y-3">
        {filteredEvents.map((event) => (
          <div
            key={event.id}
            className={`bg-white border border-gray-200 rounded-lg p-5 shadow-sm hover:shadow-md transition-shadow ${getBorderColor(
              undefined,
              event.event.type
            )} border-l-4`}
          >
            <div className="flex items-start gap-4">
              {/* Icône */}
              <div className="text-2xl flex-shrink-0">
                {getEventIcon(event.event.type)}
              </div>

              {/* Contenu */}
              <div className="flex-1 min-w-0">
                {formatEventDetails(event, false)}
                <p className="text-xs text-gray-400 mt-2">
                  {event.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          </div>
        ))}
        {/* Élément de référence pour le scroll automatique */}
        <div ref={timelineEndRef} />
      </div>
    </div>
  );
}
