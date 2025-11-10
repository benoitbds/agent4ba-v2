"use client";

import { useState, useRef, useEffect } from "react";
import { Link2, Brain, MessageSquare, FileText, Flag } from "lucide-react";
import type { TimelineEvent } from "@/types/events";

interface AgentTimelineProps {
  events: TimelineEvent[];
}

interface EventGroup {
  id: string;
  type: "node" | "standalone";
  nodeName?: string;
  events: TimelineEvent[];
  status?: "running" | "completed" | "error";
}

export default function AgentTimeline({ events }: AgentTimelineProps) {
  // État pour gérer l'ouverture/fermeture de chaque groupe
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());

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

  // Fonction pour regrouper les événements par nœud
  const groupEvents = (events: TimelineEvent[]): EventGroup[] => {
    const groups: EventGroup[] = [];
    let currentNodeGroup: EventGroup | null = null;

    events.forEach((event) => {
      const { type } = event.event;

      if (type === "node_start") {
        // Démarrer un nouveau groupe de nœud
        const nodeName = "node_name" in event.event ? event.event.node_name : "Unknown";
        currentNodeGroup = {
          id: `node-${event.id}`,
          type: "node",
          nodeName,
          events: [event],
          status: "running",
        };
      } else if (type === "node_end" && currentNodeGroup) {
        // Terminer le groupe de nœud actuel
        currentNodeGroup.events.push(event);
        currentNodeGroup.status = "completed";
        groups.push(currentNodeGroup);
        currentNodeGroup = null;
      } else if (currentNodeGroup) {
        // Ajouter l'événement au groupe actuel
        currentNodeGroup.events.push(event);
        if (type === "error") {
          currentNodeGroup.status = "error";
        }
      } else {
        // Événement standalone (pas dans un nœud)
        groups.push({
          id: `standalone-${event.id}`,
          type: "standalone",
          events: [event],
        });
      }
    });

    // Si un groupe de nœud est encore ouvert, l'ajouter
    if (currentNodeGroup) {
      groups.push(currentNodeGroup);
    }

    return groups;
  };

  const toggleGroup = (groupId: string) => {
    setOpenGroups((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(groupId)) {
        newSet.delete(groupId);
      } else {
        newSet.add(groupId);
      }
      return newSet;
    });
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case "thread_id":
        return <Link2 className="w-5 h-5" />;
      case "user_request":
        return "👤";
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
        return <FileText className="w-5 h-5" />;
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

  const groups = groupEvents(events);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">
        Timeline d&apos;exécution
      </h2>

      <div className="flex flex-col-reverse space-y-3 space-y-reverse">
        {groups.map((group) => {
          const isOpen = openGroups.has(group.id);

          if (group.type === "node") {
            // Groupe de nœud avec accordéon
            return (
              <div
                key={group.id}
                className={`bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow ${getBorderColor(
                  group.status
                )} border-l-4`}
              >
                {/* Header cliquable */}
                <button
                  onClick={() => toggleGroup(group.id)}
                  className="w-full px-6 py-4 flex items-center gap-4 hover:bg-gray-50 transition-colors text-left"
                >
                  {/* Chevron */}
                  <span className="text-gray-600 text-lg flex-shrink-0">
                    {isOpen ? "▼" : "▶"}
                  </span>

                  {/* Icône du nœud */}
                  <span className="text-xl flex-shrink-0">
                    {group.status === "completed"
                      ? "✓"
                      : group.status === "error"
                      ? "⚠"
                      : "▶"}
                  </span>

                  {/* Nom du nœud */}
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 text-base">
                      {group.nodeName}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {group.status === "completed"
                        ? "Terminé"
                        : group.status === "error"
                        ? "Erreur"
                        : "En cours..."}
                    </p>
                  </div>

                  {/* Badge avec nombre d'événements */}
                  <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    {group.events.length} événements
                  </span>
                </button>

                {/* Contenu dépliable */}
                {isOpen && (
                  <div className="border-t border-gray-100 bg-gray-50/50">
                    <div className="px-6 py-4 space-y-3">
                      {group.events.map((event) => (
                        <div
                          key={event.id}
                          className="flex items-start gap-3 p-3 bg-white rounded border border-gray-200"
                        >
                          {/* Icône */}
                          <div className="text-lg flex-shrink-0 text-gray-600">
                            {getEventIcon(event.event.type)}
                          </div>

                          {/* Contenu */}
                          <div className="flex-1 min-w-0">
                            {formatEventDetails(event, false)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          } else {
            // Événement standalone
            const event = group.events[0];
            return (
              <div
                key={group.id}
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
            );
          }
        })}
        {/* Élément de référence pour le scroll automatique */}
        <div ref={timelineEndRef} />
      </div>
    </div>
  );
}
