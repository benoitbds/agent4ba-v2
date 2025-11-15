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
 * @param token - Le token d'authentification (peut être null)
 * @returns Un objet contenant les événements de timeline et l'état de connexion
 *
 * @example
 * const { events, isConnected } = useTimelineStream(sessionId, token);
 */
export function useTimelineStream(sessionId: string | null, token: string | null) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  useEffect(() => {
    if (!sessionId || !token) {
      setEvents([]); // Réinitialiser si pas de session
      return;
    }

    const ctrl = new AbortController();
    console.log(`[TIMELINE_STREAM] Initializing for session: ${sessionId}`);
    setEvents([]); // Vider les événements précédents pour la nouvelle session
    setIsConnected(false);

    const connect = async () => {
      await fetchEventSource(`${API_URL}/api/v1/timeline/stream/${sessionId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream',
        },
        signal: ctrl.signal,

        onopen: async (response) => {
          if (response.ok && response.headers.get('content-type') === 'text/event-stream') {
            console.log('[TIMELINE_STREAM] Connection established successfully.');
            setIsConnected(true);
          } else {
            console.error(`[TIMELINE_STREAM] Failed to open connection: status=${response.status}`, response);
            setIsConnected(false);
            ctrl.abort(); // Arrêter si l'ouverture échoue
          }
        },

        onmessage(event) {
          console.log(`[TIMELINE_STREAM] Raw event received:`, event);

          if (event.data) {
            try {
              // Gérer le signal de fin spécial
              if (event.data === '[DONE]') {
                  console.log('[TIMELINE_STREAM] Received [DONE] signal. Closing connection.');
                  ctrl.abort();
                  return;
              }

              const parsedEvent: TimelineEvent = JSON.parse(event.data);
              console.log('[TIMELINE_STREAM] Parsed event:', parsedEvent);

              setEvents((prevEvents) => [...prevEvents, parsedEvent]);

            } catch (e) {
              console.error('[TIMELINE_STREAM] Failed to parse event data:', event.data, e);
            }
          } else {
            console.log('[TIMELINE_STREAM] Received an empty event, likely a keep-alive ping.');
          }
        },

        onclose() {
          console.log(`[TIMELINE_STREAM] Connection closed for session: ${sessionId}`);
          setIsConnected(false);
          // Ne pas throw d'erreur ici pour éviter les re-connexions infinies
          // si la fermeture est intentionnelle (via ctrl.abort()).
        },

        onerror(err) {
          console.error('[TIMELINE_STREAM] Connection error:', err);
          setIsConnected(false);
          // Important: Lancer l'erreur arrête les tentatives de reconnexion de la bibliothèque.
          // À n'utiliser que pour les erreurs fatales.
          throw err;
        },
      });
    };

    connect();

    // Fonction de cleanup
    return () => {
      console.log(`[TIMELINE_STREAM] Cleanup: Aborting connection for session ${sessionId}.`);
      ctrl.abort();
      setEvents([]);
      setIsConnected(false);
    };

  }, [sessionId, token]); // Dépendances explicites

  return { events, isConnected };
}
