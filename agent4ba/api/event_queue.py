"""
Système de queue pour le streaming temps réel des événements.

Ce module fournit un gestionnaire de queues thread-safe pour permettre
aux agents d'émettre des événements au fur et à mesure de leur exécution.
"""

import asyncio
import threading
from collections.abc import AsyncIterator
from typing import Any


class EventQueue:
    """Queue thread-safe pour les événements d'agents."""

    def __init__(self) -> None:
        """Initialise la queue."""
        # Utiliser une queue standard thread-safe
        import queue
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Définit la boucle d'événements asyncio.

        Args:
            loop: Boucle d'événements asyncio
        """
        self._loop = loop

    def put(self, event: dict[str, Any]) -> None:
        """
        Ajoute un événement à la queue de manière thread-safe.

        Args:
            event: Dictionnaire représentant l'événement
        """
        self._queue.put(event)

    def done(self) -> None:
        """Signale que plus aucun événement ne sera ajouté."""
        self._queue.put(None)

    async def get_events(self) -> AsyncIterator[dict[str, Any]]:
        """
        Générateur asynchrone qui yield les événements au fur et à mesure.

        Yields:
            Événements de la queue jusqu'à recevoir le signal de fin (None)
        """
        loop = asyncio.get_running_loop()

        while True:
            # Récupérer de manière asynchrone depuis une queue synchrone
            event = await loop.run_in_executor(None, self._queue.get)
            if event is None:
                break
            yield event


# Dictionnaire global pour stocker les queues par thread_id
_event_queues: dict[str, EventQueue] = {}
_queue_lock = threading.Lock()


def get_event_queue(thread_id: str) -> EventQueue:
    """
    Récupère ou crée une queue d'événements pour un thread donné.

    Args:
        thread_id: Identifiant du thread

    Returns:
        Queue d'événements pour ce thread
    """
    with _queue_lock:
        if thread_id not in _event_queues:
            _event_queues[thread_id] = EventQueue()
        return _event_queues[thread_id]


def cleanup_event_queue(thread_id: str) -> None:
    """
    Nettoie la queue d'événements pour un thread donné.

    Args:
        thread_id: Identifiant du thread
    """
    with _queue_lock:
        if thread_id in _event_queues:
            del _event_queues[thread_id]

