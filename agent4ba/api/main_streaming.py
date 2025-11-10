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
    print(f"[MERGE_STREAMS] Starting with {len(streams)} streams")
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    remaining_tasks = len(streams)

    async def consume(stream: AsyncIterator[str], stream_id: int) -> None:
        """Consomme un stream et met les éléments dans la queue."""
        nonlocal remaining_tasks
        print(f"[MERGE_STREAMS] Consumer {stream_id} started")
        item_count = 0
        try:
            async for item in stream:
                item_count += 1
                await queue.put(item)
                if item_count % 5 == 0:
                    print(f"[MERGE_STREAMS] Consumer {stream_id} put {item_count} items")
        except Exception as e:
            print(f"[MERGE_STREAMS] Consumer {stream_id} error: {e}")
            raise
        finally:
            print(f"[MERGE_STREAMS] Consumer {stream_id} finished with {item_count} items")
            # Décrémenter le compteur de tâches restantes
            remaining_tasks -= 1
            # Si c'était la dernière tâche, signaler la fin
            if remaining_tasks == 0:
                print(f"[MERGE_STREAMS] All consumers finished, signaling done")
                await queue.put(None)

    # Lancer une tâche pour chaque stream
    tasks = [asyncio.create_task(consume(stream, i)) for i, stream in enumerate(streams)]
    print(f"[MERGE_STREAMS] Created {len(tasks)} consumer tasks")

    # Yielder les éléments au fur et à mesure qu'ils arrivent
    yielded_count = 0
    print(f"[MERGE_STREAMS] Starting to yield items")
    while True:
        item = await queue.get()
        if item is None:
            print(f"[MERGE_STREAMS] Received done signal after yielding {yielded_count} items")
            break
        yielded_count += 1
        yield item

    # Attendre que toutes les tâches soient terminées
    print(f"[MERGE_STREAMS] Waiting for all tasks to complete")
    await asyncio.gather(*tasks, return_exceptions=True)
    print(f"[MERGE_STREAMS] All tasks completed")

