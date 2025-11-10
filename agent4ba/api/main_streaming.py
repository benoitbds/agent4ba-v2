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
    tasks = []

    async def consume(stream: AsyncIterator[str]) -> None:
        """Consomme un stream et met les éléments dans la queue."""
        try:
            async for item in stream:
                await queue.put(item)
        finally:
            # Signaler la fin de ce stream
            tasks.remove(asyncio.current_task())  # type: ignore
            if not tasks:
                # Si tous les streams sont terminés, signaler la fin
                await queue.put(None)

    # Lancer une tâche pour chaque stream
    for stream in streams:
        task = asyncio.create_task(consume(stream))
        tasks.append(task)

    # Yielder les éléments au fur et à mesure qu'ils arrivent
    while True:
        item = await queue.get()
        if item is None:
            break
        yield item
