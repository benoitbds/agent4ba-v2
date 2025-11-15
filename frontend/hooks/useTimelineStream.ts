/**
 * Hook React pour gérer la connexion SSE à la timeline du backend
 * Consomme le flux Server-Sent Events sur /api/v1/timeline/stream/{session_id}
 * Utilise @microsoft/fetch-event-source pour une meilleure gestion de l'authentification
 */

import { useState, useEffect } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
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

    // Créer un AbortController pour gérer l'annulation de la connexion
    const ctrl = new AbortController();

    // URL du endpoint SSE
    const eventSourceUrl = `${API_URL}/api/v1/timeline/stream/${sessionId}`;

    // Récupérer le token d'authentification depuis localStorage
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;

    // Configurer les headers d'authentification
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Lancer la connexion SSE avec fetchEventSource
    fetchEventSource(eventSourceUrl, {
      method: 'GET',
      headers,
      signal: ctrl.signal,

      // Gestionnaire pour les messages reçus
      onmessage(event) {
        // Ignorer les messages vides (keep-alive pings)
        // Le backend envoie des pings sous forme de commentaires SSE ": ping\n\n"
        // qui peuvent arriver comme des messages avec event.data vide
        if (!event.data || event.data.trim() === '') {
          return;
        }

        try {
          // Parser le JSON reçu
          const timelineEvent: TimelineEvent = JSON.parse(event.data);

          // Ajouter le nouvel événement au tableau
          setEvents((prevEvents) => [...prevEvents, timelineEvent]);
        } catch (error) {
          console.error('Failed to parse SSE event data:', event.data, error);
        }
      },

      // Gestionnaire d'erreurs
      onerror(err) {
        console.error('Erreur de connexion SSE:', err);

        // Arrêter la connexion en cas d'erreur fatale (401, 403, 404, etc.)
        // En jetant une erreur, on empêche fetchEventSource de retry automatiquement
        throw err;
      },

      // Gestionnaire de fermeture
      onclose() {
        console.log(`[TIMELINE_STREAM] Connexion fermée pour la session: ${sessionId}`);
      },

      // Désactiver le retry automatique en cas d'erreur
      // Nous gérons manuellement les reconnexions
      openWhenHidden: false,
    }).catch((error) => {
      // Gérer les erreurs qui ne sont pas des annulations
      if (error.name !== 'AbortError') {
        console.error('Erreur fatale dans le stream SSE:', error);
      }
    });

    // Fonction de nettoyage : annuler la connexion
    return () => {
      ctrl.abort();
    };
  }, [sessionId]); // Se réexécute quand sessionId change

  return events;
}
