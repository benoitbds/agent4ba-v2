"use client";

import type { TimelineEvent } from "@/types/events";

interface AgentTimelineProps {
  events: TimelineEvent[];
}

export default function AgentTimeline({ events }: AgentTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <p>En attente d&apos;événements...</p>
      </div>
    );
  }

  const getEventIcon = (type: string) => {
    switch (type) {
      case "thread_id":
        return "🔗";
      case "node_start":
        return "▶️";
      case "node_end":
        return "✅";
      case "llm_start":
        return "🤖";
      case "llm_token":
        return "💬";
      case "llm_end":
        return "🎯";
      case "impact_plan_ready":
        return "📋";
      case "workflow_complete":
        return "🏁";
      case "error":
        return "❌";
      default:
        return "📌";
    }
  };

  const getEventColor = (type: string) => {
    switch (type) {
      case "thread_id":
        return "bg-purple-100 border-purple-300";
      case "node_start":
        return "bg-blue-100 border-blue-300";
      case "node_end":
        return "bg-green-100 border-green-300";
      case "llm_start":
      case "llm_token":
      case "llm_end":
        return "bg-indigo-100 border-indigo-300";
      case "impact_plan_ready":
        return "bg-yellow-100 border-yellow-300";
      case "workflow_complete":
        return "bg-emerald-100 border-emerald-300";
      case "error":
        return "bg-red-100 border-red-300";
      default:
        return "bg-gray-100 border-gray-300";
    }
  };

  const formatEventDetails = (event: TimelineEvent) => {
    const { type } = event.event;

    switch (type) {
      case "thread_id":
        return (
          <div>
            <p className="font-semibold">Session initialisée</p>
            <p className="text-sm text-gray-600 font-mono truncate">
              Thread: {event.event.thread_id}
            </p>
          </div>
        );
      case "node_start":
        return (
          <div>
            <p className="font-semibold">Nœud démarré</p>
            <p className="text-sm text-gray-600">{event.event.node_name}</p>
          </div>
        );
      case "node_end":
        return (
          <div>
            <p className="font-semibold">Nœud terminé</p>
            <p className="text-sm text-gray-600">{event.event.node_name}</p>
            {event.event.output && (
              <details className="mt-1 text-xs">
                <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
                  Voir la sortie
                </summary>
                <pre className="mt-1 p-2 bg-gray-50 rounded overflow-x-auto">
                  {JSON.stringify(event.event.output, null, 2)}
                </pre>
              </details>
            )}
          </div>
        );
      case "impact_plan_ready":
        return (
          <div>
            <p className="font-semibold text-yellow-700">
              ImpactPlan prêt pour validation
            </p>
            <p className="text-sm text-gray-600">
              {event.event.impact_plan.new_items.length} nouveaux items
            </p>
          </div>
        );
      case "workflow_complete":
        return (
          <div>
            <p className="font-semibold text-green-700">Workflow terminé</p>
            <p className="text-sm text-gray-600">{event.event.result}</p>
          </div>
        );
      case "error":
        return (
          <div>
            <p className="font-semibold text-red-700">Erreur</p>
            <p className="text-sm text-gray-600">{event.event.error}</p>
            {event.event.details && (
              <p className="text-xs text-gray-500 mt-1">{event.event.details}</p>
            )}
          </div>
        );
      default:
        return (
          <div>
            <p className="font-semibold">{type}</p>
          </div>
        );
    }
  };

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold mb-4">Timeline d&apos;exécution</h2>
      {events.map((event, index) => (
        <div key={event.id} className="relative">
          {/* Vertical line connecting events */}
          {index < events.length - 1 && (
            <div className="absolute left-6 top-12 bottom-0 w-0.5 bg-gray-300" />
          )}

          {/* Event card */}
          <div
            className={`relative flex items-start gap-3 p-4 border rounded-lg ${getEventColor(
              event.event.type
            )}`}
          >
            {/* Icon */}
            <div className="text-2xl flex-shrink-0">
              {getEventIcon(event.event.type)}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              {formatEventDetails(event)}
              <p className="text-xs text-gray-500 mt-2">
                {event.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
