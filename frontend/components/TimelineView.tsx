"use client";

import { useRef, useEffect } from "react";
import SessionView from "./SessionView";
import type { TimelineSession } from "@/types/events";

interface TimelineViewProps {
  sessions: TimelineSession[];
  onToggleSession: (sessionId: string) => void;
}

export default function TimelineView({ sessions, onToggleSession }: TimelineViewProps) {
  // Référence pour le scroll automatique vers le haut (nouvelle session)
  const timelineTopRef = useRef<HTMLDivElement | null>(null);

  // Fonction pour scroller vers le haut (où se trouve la nouvelle session)
  const scrollToTop = () => {
    timelineTopRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Effet pour scroller automatiquement quand les sessions changent
  useEffect(() => {
    scrollToTop();
  }, [sessions.length]); // Déclencher uniquement quand le nombre de sessions change

  if (sessions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <p>En attente de requêtes...</p>
      </div>
    );
  }

  // Inverser l'ordre des sessions pour afficher les plus récentes en haut
  const reversedSessions = [...sessions].reverse();

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xl font-semibold text-gray-900 mb-4 flex-shrink-0">
        Timeline d&apos;exécution
      </h2>

      <div className="flex-1 overflow-y-auto pr-2 space-y-3">
        {/* Élément de référence pour le scroll automatique vers le haut */}
        <div ref={timelineTopRef} />
        {reversedSessions.map((session, index) => (
          <SessionView
            key={session.id}
            session={session}
            isLastSession={index === 0} // La première session affichée (plus récente)
            onToggle={onToggleSession}
          />
        ))}
      </div>
    </div>
  );
}
