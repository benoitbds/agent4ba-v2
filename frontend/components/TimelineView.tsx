"use client";

import { useRef, useEffect } from "react";
import SessionView from "./SessionView";
import type { TimelineSession } from "@/types/events";

interface TimelineViewProps {
  sessions: TimelineSession[];
  onToggleSession: (sessionId: string) => void;
}

export default function TimelineView({ sessions, onToggleSession }: TimelineViewProps) {
  // Référence pour le scroll automatique
  const timelineEndRef = useRef<HTMLDivElement | null>(null);

  // Fonction pour scroller vers le bas
  const scrollToBottom = () => {
    timelineEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Effet pour scroller automatiquement quand les sessions changent
  useEffect(() => {
    scrollToBottom();
  }, [sessions]);

  if (sessions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <p>En attente de requêtes...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">
        Timeline d&apos;exécution
      </h2>

      <div className="space-y-3">
        {sessions.map((session, index) => (
          <SessionView
            key={session.id}
            session={session}
            isLastSession={index === sessions.length - 1}
            onToggle={onToggleSession}
          />
        ))}
        {/* Élément de référence pour le scroll automatique */}
        <div ref={timelineEndRef} />
      </div>
    </div>
  );
}
