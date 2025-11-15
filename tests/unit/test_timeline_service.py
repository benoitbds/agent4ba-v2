"""Tests unitaires pour le service de timeline en temps réel."""

import asyncio
import threading
import uuid

import pytest

from agent4ba.api.timeline_service import TimelineEvent, get_timeline_service


async def _next_event(async_iter):
    """Helper pour récupérer le prochain événement avec un timeout court."""

    return await asyncio.wait_for(async_iter.__anext__(), timeout=1.0)


def test_add_event_from_thread_is_streamed_immediately():
    asyncio.run(_run_add_event_from_thread_is_streamed_immediately())


async def _run_add_event_from_thread_is_streamed_immediately():
    """Les événements ajoutés depuis un thread doivent être diffusés immédiatement."""

    service = get_timeline_service()
    session_id = str(uuid.uuid4())

    stream = service.stream_events(session_id)
    event_iterator = stream.__aiter__()

    first_event_task = asyncio.create_task(_next_event(event_iterator))

    # Laisser l'itérateur démarrer et enregistrer la boucle de session
    await asyncio.sleep(0)

    event = TimelineEvent(
        type="WORKFLOW_START",
        message="Processing query",
        status="IN_PROGRESS",
    )

    def push_event() -> None:
        service.add_event(session_id, event)

    thread = threading.Thread(target=push_event)
    thread.start()
    thread.join()

    received_event = await first_event_task
    assert received_event.message == event.message

    # Vérifier que signal_done depuis un thread ferme bien le flux
    next_event_task = asyncio.create_task(_next_event(event_iterator))

    def finish_stream() -> None:
        service.signal_done(session_id)

    closer = threading.Thread(target=finish_stream)
    closer.start()
    closer.join()

    with pytest.raises(StopAsyncIteration):
        await next_event_task

    service.cleanup_session(session_id)


def test_pending_events_are_flushed_when_loop_registered():
    asyncio.run(_run_pending_events_are_flushed_when_loop_registered())


async def _run_pending_events_are_flushed_when_loop_registered():
    """Les événements stockés avant l'abonnement SSE doivent être diffusés ensuite."""

    service = get_timeline_service()
    session_id = str(uuid.uuid4())

    pending_event = TimelineEvent(
        type="ROUTER_THOUGHT",
        message="Router analysing query",
        status="IN_PROGRESS",
    )

    def push_pending() -> None:
        service.add_event(session_id, pending_event)

    thread = threading.Thread(target=push_pending)
    thread.start()
    thread.join()

    stream = service.stream_events(session_id)
    event_iterator = stream.__aiter__()

    received_event = await _next_event(event_iterator)
    assert received_event.message == pending_event.message

    service.signal_done(session_id)

    with pytest.raises(StopAsyncIteration):
        await _next_event(event_iterator)

    service.cleanup_session(session_id)
