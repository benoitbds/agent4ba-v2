/**
 * Hook React pour gérer la connexion SSE à la timeline du backend
 * Consomme le flux Server-Sent Events sur /api/v1/timeline/stream/{session_id}
 */

import { useState, useEffect } from 'react';
import type { TimelineEvent } from '@/types/timeline';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

/**
 * Hook personnalisé pour consommer le flux SSE de timeline
 *
 * @param sessionId - L'ID de session pour se connecter au flux SSE (peut être null)
 * @returns Un tableau d'événements de timeline reçus en temps réel
 *
 * @example
 * const timelineEvents = useTimelineStream(sessionId);
 */
export function useTimelineStream(sessionId: string | null): TimelineEvent[] {
  const [events, setEvents] = useState<TimelineEvent[]>([]);

  useEffect(() => {
    // Ne rien faire si aucun sessionId n'est fourni
    if (!sessionId) {
      // Réinitialiser les événements quand sessionId devient null
      setEvents([]);
      return;
    }

    // Créer la connexion EventSource
    const eventSourceUrl = `${API_URL}/api/v1/timeline/stream/${sessionId}`;

    // Récupérer le token d'authentification
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;

    // Note: EventSource ne supporte pas nativement les headers personnalisés
    // Si l'authentification est requise, on doit passer le token dans l'URL
    // ou utiliser une approche alternative
    const urlWithAuth = token ? `${eventSourceUrl}?token=${encodeURIComponent(token)}` : eventSourceUrl;

    const eventSource = new EventSource(urlWithAuth);

    // Gestionnaire pour les messages reçus
    eventSource.onmessage = (event) => {
      try {
        // Parser le JSON reçu
        const timelineEvent: TimelineEvent = JSON.parse(event.data);

        // Ajouter le nouvel événement au tableau
        setEvents((prevEvents) => [...prevEvents, timelineEvent]);
      } catch (error) {
        console.error('Erreur lors du parsing de l\'événement SSE:', error, event.data);
      }
    };

    // Gestionnaire d'erreurs
    eventSource.onerror = (error) => {
      console.error('Erreur de connexion SSE:', error);

      // Fermer la connexion en cas d'erreur
      eventSource.close();
    };

    // Fonction de nettoyage : fermer la connexion EventSource
    return () => {
      eventSource.close();
    };
  }, [sessionId]); // Se réexécute quand sessionId change

  return events;
}
