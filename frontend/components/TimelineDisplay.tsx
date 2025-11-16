/**
 * Composant d'affichage de la timeline en temps réel
 * Affiche les événements TimelineEvent reçus via SSE
 */

"use client";

import { useEffect, useRef } from 'react';
import type { TimelineEvent } from '@/types/timeline';
import MermaidDiagram from './MermaidDiagram';

interface TimelineDisplayProps {
  events: TimelineEvent[];
}

/**
 * Retourne l'icône appropriée pour chaque type d'événement
 */
function getEventIcon(type: TimelineEvent['type']): string {
  switch (type) {
    case 'WORKFLOW_START':
      return '🚀';
    case 'TASK_REWRITTEN':
      return '✏️';
    case 'ROUTER_DECIDING':
      return '🤔';
    case 'ROUTER_THOUGHT':
      return '💭';
    case 'ROUTER_DECISION':
      return '✅';
    case 'AGENT_START':
      return '🤖';
    case 'AGENT_COMPLETE':
      return '✓';
    case 'WORKFLOW_COMPLETE':
      return '🎉';
    default:
      return '📍';
  }
}

/**
 * Retourne la couleur de badge appropriée pour chaque statut
 */
function getStatusColor(status: TimelineEvent['status']): string {
  switch (status) {
    case 'IN_PROGRESS':
      return 'bg-blue-100 text-blue-800 border-blue-300';
    case 'SUCCESS':
      return 'bg-green-100 text-green-800 border-green-300';
    case 'ERROR':
      return 'bg-red-100 text-red-800 border-red-300';
    case 'WAITING':
      return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300';
  }
}

/**
 * Formate un timestamp ISO en format lisible
 */
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch (error) {
    return timestamp;
  }
}

/**
 * Détecte si un message contient un bloc de code Mermaid
 */
function isMermaidCode(message: string): boolean {
  return message.trim().startsWith('```mermaid');
}

/**
 * Extrait le code Mermaid d'un message
 */
function extractMermaidCode(message: string): string {
  const lines = message.trim().split('\n');
  // Retirer la première ligne (```mermaid) et la dernière (```)
  return lines.slice(1, -1).join('\n');
}

/**
 * Composant d'affichage de la timeline
 */
export default function TimelineDisplay({ events }: TimelineDisplayProps) {
  const timelineEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll vers le bas quand de nouveaux événements arrivent
  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <div className="text-center">
          <div className="text-4xl mb-2">⏳</div>
          <p>En attente d&apos;événements...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xl font-semibold text-gray-900 mb-4 flex-shrink-0">
        Execution Timeline
      </h2>

      <div className="flex-1 overflow-y-auto pr-2 space-y-2">
        {events.map((event, index) => (
          <div
            key={event.event_id}
            className="timeline-event-enter bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
            style={{
              animation: 'slideIn 0.3s ease-out',
            }}
          >
            {/* Header de l'événement */}
            <div className="flex items-start gap-3">
              {/* Icône */}
              <div className="text-2xl flex-shrink-0">
                {getEventIcon(event.type)}
              </div>

              {/* Contenu */}
              <div className="flex-1 min-w-0">
                {/* Titre et timestamp */}
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 text-sm">
                      {event.type.replace(/_/g, ' ')}
                    </h3>
                    {event.agent_name && (
                      <p className="text-xs text-gray-500">
                        Agent: <span className="font-medium">{event.agent_name}</span>
                      </p>
                    )}
                  </div>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {formatTimestamp(event.timestamp)}
                  </span>
                </div>

                {/* Message ou Diagramme Mermaid */}
                {isMermaidCode(event.message) ? (
                  <div className="mb-2">
                    <MermaidDiagram code={extractMermaidCode(event.message)} />
                  </div>
                ) : (
                  <p className="text-sm text-gray-700 mb-2">
                    {event.message}
                  </p>
                )}

                {/* Status badge */}
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-block px-2 py-1 text-xs font-medium rounded border ${getStatusColor(
                      event.status
                    )}`}
                  >
                    {event.status}
                  </span>
                </div>

                {/* Details (si présents) */}
                {event.details && Object.keys(event.details).length > 0 && (
                  <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                    <details>
                      <summary className="cursor-pointer font-medium text-gray-700">
                        Détails
                      </summary>
                      <pre className="mt-1 text-gray-600 overflow-x-auto">
                        {JSON.stringify(event.details, null, 2)}
                      </pre>
                    </details>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Élément de référence pour le scroll automatique */}
        <div ref={timelineEndRef} />
      </div>

      <style jsx>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
