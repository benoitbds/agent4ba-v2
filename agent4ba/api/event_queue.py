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

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Initialise la queue.

        Args:
            loop: Boucle d'événements asyncio
        """
        self._loop = loop
        self._queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    def put(self, event: dict[str, Any]) -> None:
        """
        Ajoute un événement à la queue de manière thread-safe.

        Peut être appelé depuis un thread synchrone (agents).

        Args:
            event: Dictionnaire représentant l'événement
        """
        # Utiliser call_soon_threadsafe pour mettre l'événement depuis n'importe quel thread
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)

    def done(self) -> None:
        """Signale que plus aucun événement ne sera ajouté."""
        self._loop.call_soon_threadsafe(self._queue.put_nowait, None)

    async def get_events(self) -> AsyncIterator[dict[str, Any]]:
        """
        Générateur asynchrone qui yield les événements au fur et à mesure.

        Yields:
            Événements de la queue jusqu'à recevoir le signal de fin (None)
        """
        print("[EVENT_QUEUE] get_events() started")
        event_count = 0
        while True:
            print(f"[EVENT_QUEUE] Waiting for event #{event_count + 1}...")
            event = await self._queue.get()
            if event is None:
                print(f"[EVENT_QUEUE] Received done signal after {event_count} events")
                break
            event_count += 1
            print(f"[EVENT_QUEUE] Yielding event #{event_count}: {event.get('type')}")
            yield event
        print(f"[EVENT_QUEUE] get_events() finished with {event_count} events")


# Dictionnaire global pour stocker les queues par thread_id
_event_queues: dict[str, EventQueue] = {}
_queue_lock = threading.Lock()


def get_event_queue(thread_id: str, loop: asyncio.AbstractEventLoop | None = None) -> EventQueue:
    """
    Récupère ou crée une queue d'événements pour un thread donné.

    Args:
        thread_id: Identifiant du thread
        loop: Boucle d'événements asyncio (requis pour la création)

    Returns:
        Queue d'événements pour ce thread
    """
    with _queue_lock:
        if thread_id not in _event_queues:
            if loop is None:
                # Essayer de récupérer la boucle courante
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    raise ValueError("No event loop available and none provided")
            _event_queues[thread_id] = EventQueue(loop)
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

