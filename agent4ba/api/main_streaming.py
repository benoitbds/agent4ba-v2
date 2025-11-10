"""
Helper pour le streaming d'événements SSE en temps réel.

Ce module fournit des utilitaires pour merger le streaming de la queue
d'événements avec le streaming LangGraph.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any


async def merge_streams(
    *streams: AsyncIterator[str],
) -> AsyncIterator[str]:
    """
    Merge plusieurs async iterators en un seul stream.

    Args:
        *streams: Générateurs asynchrones à merger

    Yields:
        Éléments de tous les streams au fur et à mesure qu'ils arrivent
    """
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    remaining_tasks = len(streams)

    async def consume(stream: AsyncIterator[str]) -> None:
        """Consomme un stream et met les éléments dans la queue."""
        nonlocal remaining_tasks
        try:
            async for item in stream:
                await queue.put(item)
        finally:
            # Décrémenter le compteur de tâches restantes
            remaining_tasks -= 1
            # Si c'était la dernière tâche, signaler la fin
            if remaining_tasks == 0:
                await queue.put(None)

    # Lancer une tâche pour chaque stream
    tasks = [asyncio.create_task(consume(stream)) for stream in streams]

    # Yielder les éléments au fur et à mesure qu'ils arrivent
    while True:
        item = await queue.get()
        if item is None:
            break
        yield item

    # Attendre que toutes les tâches soient terminées
    await asyncio.gather(*tasks, return_exceptions=True)

