"""
Système de queue pour le streaming temps réel des événements.

Ce module fournit un gestionnaire de queues thread-safe pour permettre
aux agents d'émettre des événements au fur et à mesure de leur exécution.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any


class EventQueue:
    """Queue thread-safe pour les événements d'agents."""

    def __init__(self) -> None:
        """Initialise la queue."""
        self._queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    def put(self, event: dict[str, Any]) -> None:
        """
        Ajoute un événement à la queue de manière thread-safe.

        Args:
            event: Dictionnaire représentant l'événement
        """
        # put_nowait est thread-safe dans asyncio
        self._queue.put_nowait(event)

    def done(self) -> None:
        """Signale que plus aucun événement ne sera ajouté."""
        self._queue.put_nowait(None)

    async def get_events(self) -> AsyncIterator[dict[str, Any]]:
        """
        Générateur asynchrone qui yield les événements au fur et à mesure.

        Yields:
            Événements de la queue jusqu'à recevoir le signal de fin (None)
        """
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield event


# Dictionnaire global pour stocker les queues par thread_id
_event_queues: dict[str, EventQueue] = {}


def get_event_queue(thread_id: str) -> EventQueue:
    """
    Récupère ou crée une queue d'événements pour un thread donné.

    Args:
        thread_id: Identifiant du thread

    Returns:
        Queue d'événements pour ce thread
    """
    if thread_id not in _event_queues:
        _event_queues[thread_id] = EventQueue()
    return _event_queues[thread_id]


def cleanup_event_queue(thread_id: str) -> None:
    """
    Nettoie la queue d'événements pour un thread donné.

    Args:
        thread_id: Identifiant du thread
    """
    if thread_id in _event_queues:
        del _event_queues[thread_id]
