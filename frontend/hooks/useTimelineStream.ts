/**
 * Hook React pour gérer la connexion SSE à la timeline du backend
 * Consomme le flux Server-Sent Events sur /timeline/stream/{session_id}
 * Utilise @microsoft/fetch-event-source pour une meilleure gestion de l'authentification
 */

import { useState, useEffect } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import type { TimelineEvent } from '@/types/timeline';

/**
 * Fonction utilitaire pour construire l'URL de l'API en évitant les doubles slashs
 *
 * @param path - Le chemin relatif de l'endpoint (ex: '/api/v1/timeline/stream')
 * @returns L'URL complète sans doubles slashs ni duplication de /api
 */
function getApiUrl(path: string): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

  // Supprimer le slash final de la base si présent
  let cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;

  // S'assurer que le chemin commence par un slash
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  // Si la base se termine par /api et que le path commence par /api,
  // enlever /api de la base pour éviter /api/api
  if (cleanBase.endsWith('/api') && cleanPath.startsWith('/api')) {
    cleanBase = cleanBase.slice(0, -4); // Enlever '/api'
  }

  return `${cleanBase}${cleanPath}`;
}

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

    // Construire l'URL avec la fonction utilitaire pour éviter les doubles slashs
    const eventSourceUrl = getApiUrl(`/timeline/stream/${sessionId}`);
    console.log(`[TIMELINE_STREAM] Initializing for session: ${sessionId}`);
    console.log(`[TIMELINE_STREAM] EventSource URL: ${eventSourceUrl}`);

    setEvents([]); // Vider les événements précédents pour la nouvelle session
    setIsConnected(false);

    const connect = async () => {
      await fetchEventSource(eventSourceUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream',
        },
        signal: ctrl.signal,

        onopen: async (response) => {
          // Récupérer le content-type de la réponse
          const contentType = response.headers.get('content-type');

          // Logger systématiquement le statut et le content-type
          console.log(`[TIMELINE_STREAM] onopen: status=${response.status}, content-type='${contentType}'`);

          // Valider la connexion : statut OK ET content-type correct
          if (response.ok && contentType?.startsWith('text/event-stream')) {
            console.log('[TIMELINE_STREAM] ✓ Connection established successfully. EventStream is valid.');
            setIsConnected(true);
          } else {
            // Message d'erreur explicite en cas d'échec
            const errorMsg = `[TIMELINE_STREAM] ✗ Échec de la validation de la connexion EventStream. ` +
              `Attendu 'text/event-stream' mais reçu '${contentType}'. ` +
              `Vérifiez la configuration du proxy serveur et l'URL de l'API.`;
            console.error(errorMsg);
            console.error(`[TIMELINE_STREAM] Response details:`, {
              status: response.status,
              statusText: response.statusText,
              contentType: contentType,
              url: eventSourceUrl
            });

            setIsConnected(false);
            ctrl.abort(); // Annuler la connexion si la validation échoue
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
