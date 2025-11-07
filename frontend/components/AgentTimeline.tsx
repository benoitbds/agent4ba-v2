"use client";

import { useState, useEffect } from "react";
import {
  ChevronRight,
  ChevronDown,
  Play,
  CheckCircle,
  XCircle,
  Link2,
  Brain,
  MessageSquare,
  Target,
  FileText,
  Flag,
  AlertCircle,
} from "lucide-react";
import type { TimelineEvent } from "@/types/events";

interface AgentTimelineProps {
  events: TimelineEvent[];
}

interface NodeGroup {
  id: string;
  nodeName: string;
  startEvent: TimelineEvent;
  endEvent?: TimelineEvent;
  innerEvents: TimelineEvent[];
  isExpanded: boolean;
}

export default function AgentTimeline({ events }: AgentTimelineProps) {
  const [nodeGroups, setNodeGroups] = useState<Map<string, NodeGroup>>(new Map());
  const [standaloneEvents, setStandaloneEvents] = useState<TimelineEvent[]>([]);

  // Grouper les événements par nodes
  useEffect(() => {
    const groups = new Map<string, NodeGroup>();
    const standalone: TimelineEvent[] = [];
    let currentNodeId: string | null = null;

    events.forEach((event) => {
      const { type } = event.event;

      if (type === "node_start") {
        const nodeId = `${event.event.node_name}-${event.timestamp.getTime()}`;
        currentNodeId = nodeId;
        groups.set(nodeId, {
          id: nodeId,
          nodeName: event.event.node_name,
          startEvent: event,
          innerEvents: [],
          isExpanded: false, // Replié par défaut
        });
      } else if (type === "node_end" && currentNodeId) {
        const group = groups.get(currentNodeId);
        if (group) {
          group.endEvent = event;
        }
        currentNodeId = null;
      } else if (currentNodeId && (type === "llm_start" || type === "llm_token" || type === "llm_end")) {
        // Événements LLM appartiennent au node courant
        const group = groups.get(currentNodeId);
        if (group) {
          group.innerEvents.push(event);
        }
      } else {
        // Événements standalone (thread_id, impact_plan_ready, workflow_complete, error)
        standalone.push(event);
      }
    });

    setNodeGroups(groups);
    setStandaloneEvents(standalone);
  }, [events]);

  const toggleNode = (nodeId: string) => {
    setNodeGroups((prev) => {
      const newGroups = new Map(prev);
      const group = newGroups.get(nodeId);
      if (group) {
        group.isExpanded = !group.isExpanded;
      }
      return newGroups;
    });
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case "thread_id":
        return <Link2 className="w-5 h-5" />;
      case "node_start":
        return <Play className="w-5 h-5" />;
      case "node_end":
        return <CheckCircle className="w-5 h-5" />;
      case "llm_start":
        return <Brain className="w-5 h-5" />;
      case "llm_token":
        return <MessageSquare className="w-5 h-5" />;
      case "llm_end":
        return <Target className="w-5 h-5" />;
      case "impact_plan_ready":
        return <FileText className="w-5 h-5" />;
      case "workflow_complete":
        return <Flag className="w-5 h-5" />;
      case "error":
        return <XCircle className="w-5 h-5" />;
      default:
        return <AlertCircle className="w-5 h-5" />;
    }
  };

  const getEventColors = (type: string) => {
    switch (type) {
      case "thread_id":
        return "bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-300";
      case "node_start":
        return "bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300";
      case "node_end":
        return "bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300";
      case "llm_start":
      case "llm_token":
      case "llm_end":
        return "bg-indigo-50 dark:bg-indigo-950 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300";
      case "impact_plan_ready":
        return "bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800 text-yellow-700 dark:text-yellow-300";
      case "workflow_complete":
        return "bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300";
      case "error":
        return "bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300";
      default:
        return "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300";
    }
  };

  const formatEventContent = (event: TimelineEvent) => {
    const { type } = event.event;

    switch (type) {
      case "thread_id":
        return (
          <div>
            <p className="font-semibold">Session initialisée</p>
            <p className="text-sm opacity-80 font-mono truncate mt-1">
              Thread: {event.event.thread_id}
            </p>
          </div>
        );
      case "node_start":
        return (
          <div>
            <p className="font-semibold">Démarrage du nœud</p>
            <p className="text-sm opacity-80 mt-1">{event.event.node_name}</p>
          </div>
        );
      case "node_end":
        return (
          <div>
            <p className="font-semibold">Nœud terminé</p>
            <p className="text-sm opacity-80 mt-1">{event.event.node_name}</p>
          </div>
        );
      case "llm_start":
        return (
          <div>
            <p className="font-semibold">LLM démarré</p>
            {event.event.model && (
              <p className="text-sm opacity-80 mt-1">Modèle: {event.event.model}</p>
            )}
          </div>
        );
      case "llm_end":
        return (
          <div>
            <p className="font-semibold">LLM terminé</p>
            {event.event.content && (
              <p className="text-sm opacity-80 mt-1 truncate">
                {event.event.content.substring(0, 100)}...
              </p>
            )}
          </div>
        );
      case "impact_plan_ready":
        return (
          <div>
            <p className="font-semibold">Plan d&apos;impact prêt</p>
            <p className="text-sm opacity-80 mt-1">
              {event.event.impact_plan.new_items.length} nouveaux items
            </p>
          </div>
        );
      case "workflow_complete":
        return (
          <div>
            <p className="font-semibold">Workflow terminé</p>
            <p className="text-sm opacity-80 mt-1">{event.event.result}</p>
          </div>
        );
      case "error":
        return (
          <div>
            <p className="font-semibold">Erreur</p>
            <p className="text-sm opacity-80 mt-1">{event.event.error}</p>
            {event.event.details && (
              <p className="text-xs opacity-60 mt-1">{event.event.details}</p>
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

  const renderNodeGroup = (group: NodeGroup) => {
    const hasOutput = group.endEvent?.event.type === "node_end" && group.endEvent.event.output;
    const hasContent = hasOutput || group.innerEvents.length > 0;

    return (
      <div
        key={group.id}
        className="animate-fade-in border-2 rounded-lg overflow-hidden transition-all duration-200
                   bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950
                   border-blue-200 dark:border-blue-800 shadow-sm hover:shadow-md"
      >
        {/* Header du node (cliquable) */}
        <button
          onClick={() => toggleNode(group.id)}
          className="w-full flex items-center gap-3 p-4 text-left hover:bg-blue-100 dark:hover:bg-blue-900
                     transition-colors duration-150"
        >
          {/* Icône d'expansion */}
          <div className="flex-shrink-0 text-blue-600 dark:text-blue-400">
            {group.isExpanded ? (
              <ChevronDown className="w-5 h-5" />
            ) : (
              <ChevronRight className="w-5 h-5" />
            )}
          </div>

          {/* Icône du node */}
          <div className="flex-shrink-0 text-blue-600 dark:text-blue-400">
            {group.endEvent ? (
              <CheckCircle className="w-6 h-6" />
            ) : (
              <Play className="w-6 h-6 animate-pulse" />
            )}
          </div>

          {/* Contenu du header */}
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-blue-900 dark:text-blue-100">
              {group.nodeName}
            </p>
            <div className="flex items-center gap-3 mt-1">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                {group.startEvent.timestamp.toLocaleTimeString()}
              </p>
              {group.endEvent && (
                <>
                  <span className="text-xs text-blue-500">→</span>
                  <p className="text-xs text-blue-700 dark:text-blue-300">
                    {group.endEvent.timestamp.toLocaleTimeString()}
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Badge du nombre d'événements */}
          {hasContent && (
            <div className="flex-shrink-0 px-2 py-1 bg-blue-200 dark:bg-blue-800 rounded-full">
              <p className="text-xs font-semibold text-blue-800 dark:text-blue-200">
                {group.innerEvents.length + (hasOutput ? 1 : 0)}
              </p>
            </div>
          )}
        </button>

        {/* Contenu déplié */}
        {group.isExpanded && hasContent && (
          <div className="border-t-2 border-blue-200 dark:border-blue-800 bg-white dark:bg-gray-900">
            <div className="p-4 space-y-2">
              {/* Événements internes (LLM) */}
              {group.innerEvents.map((event, idx) => (
                <div
                  key={`${event.id}-${idx}`}
                  className={`flex items-start gap-3 p-3 rounded-lg border transition-all duration-150
                              ${getEventColors(event.event.type)} animate-fade-in`}
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <div className="flex-shrink-0">{getEventIcon(event.event.type)}</div>
                  <div className="flex-1 min-w-0">
                    {formatEventContent(event)}
                    <p className="text-xs opacity-60 mt-2">
                      {event.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}

              {/* Output du node_end */}
              {group.endEvent?.event.type === "node_end" && group.endEvent.event.output && (
                <details className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <summary className="cursor-pointer font-semibold text-gray-700 dark:text-gray-300
                                      hover:text-gray-900 dark:hover:text-gray-100 transition-colors">
                    Voir la sortie du nœud
                  </summary>
                  <pre className="mt-3 p-3 bg-white dark:bg-gray-900 rounded text-xs overflow-x-auto
                                  border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200">
                    {JSON.stringify(group.endEvent.event.output, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderStandaloneEvent = (event: TimelineEvent) => {
    return (
      <div
        key={event.id}
        className={`animate-fade-in flex items-start gap-3 p-4 border-2 rounded-lg transition-all duration-200
                    ${getEventColors(event.event.type)} shadow-sm hover:shadow-md`}
      >
        <div className="flex-shrink-0">{getEventIcon(event.event.type)}</div>
        <div className="flex-1 min-w-0">
          {formatEventContent(event)}
          <p className="text-xs opacity-60 mt-2">
            {event.timestamp.toLocaleTimeString()}
          </p>
        </div>
      </div>
    );
  };

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        <Brain className="w-12 h-12 mb-3 opacity-50" />
        <p className="text-lg">En attente d&apos;événements...</p>
      </div>
    );
  }

  // Créer une liste ordonnée combinant nodes et standalone events
  const allItems: Array<{ type: "node" | "standalone"; data: NodeGroup | TimelineEvent }> = [];

  nodeGroups.forEach((group) => {
    allItems.push({ type: "node", data: group });
  });

  standaloneEvents.forEach((event) => {
    allItems.push({ type: "standalone", data: event });
  });

  // Trier par timestamp (plus récent en premier)
  allItems.sort((a, b) => {
    const timeA = a.type === "node"
      ? (a.data as NodeGroup).startEvent.timestamp.getTime()
      : (a.data as TimelineEvent).timestamp.getTime();
    const timeB = b.type === "node"
      ? (b.data as NodeGroup).startEvent.timestamp.getTime()
      : (b.data as TimelineEvent).timestamp.getTime();
    return timeB - timeA;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 mb-6">
        <Brain className="w-6 h-6 text-primary-600 dark:text-primary-400" />
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          Timeline d&apos;exécution
        </h2>
      </div>

      <div className="space-y-3">
        {allItems.map((item) =>
          item.type === "node"
            ? renderNodeGroup(item.data as NodeGroup)
            : renderStandaloneEvent(item.data as TimelineEvent)
        )}
      </div>
    </div>
  );
}
