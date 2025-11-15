#!/usr/bin/env python3
"""
Script de test pour vérifier que les imports et la création d'événements fonctionnent.
"""

import sys
import traceback

def test_imports():
    """Test les imports de base."""
    try:
        print("Testing timeline service imports...")
        from agent4ba.api.timeline_service import TimelineEvent, TimelineService, get_timeline_service
        print("✓ Timeline service imports successful")

        # Créer un événement de test
        print("\nTesting TimelineEvent creation...")
        event = TimelineEvent(
            type="TEST_EVENT",
            message="This is a test event",
            status="SUCCESS",
            agent_name="test_agent",
            details={"test_key": "test_value"}
        )
        print(f"✓ TimelineEvent created: {event.type}")
        print(f"  Event ID: {event.event_id}")
        print(f"  Timestamp: {event.timestamp}")
        print(f"  Message: {event.message}")

        # Tester le service
        print("\nTesting TimelineService...")
        service = get_timeline_service()
        print(f"✓ TimelineService instance created: {type(service)}")

        # Tester l'ajout d'un événement (sans boucle async)
        print("\nTesting event storage...")
        session_id = "test_session_123"
        service.add_event(session_id, event)
        print(f"✓ Event added to session: {session_id}")

        # Récupérer les événements
        events = service.get_events(session_id)
        print(f"✓ Retrieved {len(events)} events from session")

        print("\n✓✓✓ All tests passed! ✓✓✓")
        return True

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
