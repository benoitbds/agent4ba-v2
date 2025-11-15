"""
Service de gestion des événements de timeline pour le suivi temps réel des workflows.

Ce module fournit un service centralisé pour stocker et diffuser les événements
de progression d'un workflow agentique via Server-Sent Events (SSE).
"""

import asyncio
import threading
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from agent4ba.core.logger import setup_logger

# Configurer le logger
logger = setup_logger(__name__)


class TimelineEvent(BaseModel):
    """
    Modèle d'événement de timeline pour le suivi des workflows.

    Attributes:
        event_id: Identifiant unique de l'événement (UUID)
        timestamp: Horodatage de l'événement au format ISO 8601
        type: Type d'événement (ex: "ROUTER_THOUGHT", "AGENT_ACTION", "NODE_START")
        agent_name: Nom de l'agent concerné (optionnel)
        message: Message décrivant l'événement
        status: Statut de l'événement (ex: "IN_PROGRESS", "SUCCESS", "ERROR")
        details: Détails additionnels sous forme de dictionnaire (optionnel)
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identifiant unique de l'événement",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Horodatage au format ISO 8601",
    )
    type: str = Field(..., description="Type d'événement")
    agent_name: str | None = Field(None, description="Nom de l'agent (optionnel)")
    message: str = Field(..., description="Message descriptif de l'événement")
    status: str = Field(
        default="IN_PROGRESS",
        description="Statut de l'événement",
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Détails additionnels (optionnel)",
    )


class TimelineService:
    """
    Service singleton pour gérer les événements de timeline par session.

    Ce service maintient une queue d'événements par session_id et permet
    de diffuser ces événements en temps réel via SSE.

    Attributes:
        _queues: Dictionnaire des queues d'événements par session_id
        _events: Dictionnaire des listes d'événements par session_id (historique)
        _lock: Verrou pour la synchronisation thread-safe
    """

    _instance: "TimelineService | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "TimelineService":
        """
        Implémentation du pattern Singleton.

        Returns:
            Instance unique du TimelineService
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialise le service (une seule fois grâce au singleton)."""
        if self._initialized:
            return

        self._queues: dict[str, asyncio.Queue[TimelineEvent | None]] = {}
        self._events: dict[str, list[TimelineEvent]] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._initialized = True

        logger.info("[TIMELINE_SERVICE] Service initialized")

    def _get_or_create_queue(self, session_id: str) -> asyncio.Queue[TimelineEvent | None]:
        """
        Récupère ou crée une queue pour une session donnée.

        Args:
            session_id: Identifiant de la session

        Returns:
            Queue d'événements pour cette session
        """
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
            self._events[session_id] = []
            logger.info(f"[TIMELINE_SERVICE] Created queue for session: {session_id}")

        return self._queues[session_id]

    def add_event(self, session_id: str, event: TimelineEvent) -> None:
        """
        Ajoute un événement à la timeline d'une session.

        Cette méthode est thread-safe et peut être appelée depuis n'importe quel thread.

        Args:
            session_id: Identifiant de la session
            event: Événement à ajouter
        """
        try:
            # Récupérer la boucle d'événements courante ou en créer une
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # Pas de boucle courante, on utilise call_soon_threadsafe n'est pas possible
                # On doit créer une tâche dans la boucle principale
                logger.warning(
                    f"[TIMELINE_SERVICE] No running loop for session {session_id}, "
                    "event may not be queued immediately"
                )
                # Pour le moment, on stocke juste dans l'historique
                if session_id not in self._events:
                    self._events[session_id] = []
                self._events[session_id].append(event)
                return

            # Ajouter l'événement à la queue de manière thread-safe
            queue = self._get_or_create_queue(session_id)

            # Ajouter à l'historique
            if session_id not in self._events:
                self._events[session_id] = []
            self._events[session_id].append(event)

            # Mettre l'événement dans la queue de manière thread-safe
            loop.call_soon_threadsafe(queue.put_nowait, event)

            logger.debug(
                f"[TIMELINE_SERVICE] Added event to session {session_id}: "
                f"{event.type} - {event.message}"
            )

        except Exception as e:
            logger.error(
                f"[TIMELINE_SERVICE] Error adding event to session {session_id}: {e}",
                exc_info=True,
            )

    def signal_done(self, session_id: str) -> None:
        """
        Signale qu'aucun autre événement ne sera ajouté à cette session.

        Args:
            session_id: Identifiant de la session
        """
        try:
            if session_id in self._queues:
                try:
                    loop = asyncio.get_running_loop()
                    queue = self._queues[session_id]
                    loop.call_soon_threadsafe(queue.put_nowait, None)
                    logger.info(f"[TIMELINE_SERVICE] Signaled done for session: {session_id}")
                except RuntimeError:
                    logger.warning(
                        f"[TIMELINE_SERVICE] No running loop to signal done for session {session_id}"
                    )
        except Exception as e:
            logger.error(
                f"[TIMELINE_SERVICE] Error signaling done for session {session_id}: {e}",
                exc_info=True,
            )

    async def stream_events(self, session_id: str) -> AsyncIterator[TimelineEvent]:
        """
        Stream les événements d'une session au fur et à mesure.

        Cette méthode est un générateur asynchrone qui yield les événements
        jusqu'à ce que le signal de fin soit reçu.

        Args:
            session_id: Identifiant de la session

        Yields:
            Événements de timeline au fur et à mesure de leur ajout
        """
        queue = self._get_or_create_queue(session_id)
        logger.info(f"[TIMELINE_SERVICE] Starting stream for session: {session_id}")

        event_count = 0
        try:
            while True:
                # Attendre le prochain événement
                event = await queue.get()

                # None signale la fin du stream
                if event is None:
                    logger.info(
                        f"[TIMELINE_SERVICE] Stream ended for session {session_id} "
                        f"after {event_count} events"
                    )
                    break

                event_count += 1
                logger.debug(
                    f"[TIMELINE_SERVICE] Streaming event #{event_count} for session {session_id}: "
                    f"{event.type}"
                )
                yield event

        except Exception as e:
            logger.error(
                f"[TIMELINE_SERVICE] Error streaming events for session {session_id}: {e}",
                exc_info=True,
            )

    def get_events(self, session_id: str) -> list[TimelineEvent]:
        """
        Récupère tous les événements stockés pour une session.

        Args:
            session_id: Identifiant de la session

        Returns:
            Liste des événements de la session
        """
        return self._events.get(session_id, [])

    def cleanup_session(self, session_id: str) -> None:
        """
        Nettoie les ressources associées à une session.

        Args:
            session_id: Identifiant de la session
        """
        try:
            if session_id in self._queues:
                del self._queues[session_id]
                logger.info(f"[TIMELINE_SERVICE] Cleaned up queue for session: {session_id}")

            if session_id in self._events:
                event_count = len(self._events[session_id])
                del self._events[session_id]
                logger.info(
                    f"[TIMELINE_SERVICE] Cleaned up {event_count} events for session: {session_id}"
                )

            if session_id in self._session_locks:
                del self._session_locks[session_id]

        except Exception as e:
            logger.error(
                f"[TIMELINE_SERVICE] Error cleaning up session {session_id}: {e}",
                exc_info=True,
            )


# Instance globale du service (singleton)
_timeline_service: TimelineService | None = None


def get_timeline_service() -> TimelineService:
    """
    Récupère l'instance singleton du TimelineService.

    Returns:
        Instance du TimelineService
    """
    global _timeline_service
    if _timeline_service is None:
        _timeline_service = TimelineService()
    return _timeline_service
