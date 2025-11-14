"""Test d'intégration du workflow avec le mécanisme de fallback."""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))


def test_workflow_with_fallback():
    """Teste le workflow complet avec une requête hors-scope."""
    from agent4ba.ai.graph import app as workflow_app

    print(f"\n{'='*60}")
    print(f"Testing complete workflow with out-of-scope query")
    print(f"{'='*60}\n")

    # Configuration de l'état initial
    initial_state = {
        "project_id": "test-project",
        "user_query": "c'est quoi la météo ?",
        "document_content": "",
        "context": None,
        "rewritten_task": "",
        "intent": {},
        "intent_args": {},
        "next_node": "",
        "agent_id": "",
        "agent_task": "",
        "impact_plan": {},
        "status": "",
        "approval_decision": None,
        "result": "",
        "agent_events": [],
        "thread_id": "test-thread-123",
        "ambiguous_intent": False,
        "clarification_needed": False,
        "clarification_question": None,
        "user_response": None,
    }

    print("Initial state:")
    print(f"  User query: {initial_state['user_query']}")
    print(f"  Project ID: {initial_state['project_id']}")
    print()

    # Configurer le thread
    config = {"configurable": {"thread_id": "test-thread-123"}}

    try:
        # Exécuter le workflow
        print("Executing workflow...")
        final_state = None
        for state in workflow_app.stream(initial_state, config):
            # Afficher les nœuds traversés
            if state:
                node_name = list(state.keys())[0] if state else "unknown"
                print(f"  → Passed through node: {node_name}")
                final_state = state.get(node_name, {})

        print()
        print("Workflow completed!")
        print()
        print("Final state:")
        print(f"  Status: {final_state.get('status', 'N/A')}")
        print(f"  Agent ID: {final_state.get('agent_id', 'N/A')}")
        print(f"  Agent Task: {final_state.get('agent_task', 'N/A')}")
        print(f"  Result:")
        result = final_state.get('result', 'N/A')
        if result and len(result) > 200:
            print(f"  {result[:200]}...")
        else:
            print(f"  {result}")
        print()

        # Vérifications
        assert final_state is not None, "Final state should not be None"
        assert final_state.get('status') == 'completed', f"Expected status 'completed', got '{final_state.get('status')}'"
        assert 'Désolé' in final_state.get('result', ''), "Expected 'Désolé' in result message"

        print("✓ All workflow assertions passed")
        print()
        print("Expected flow: ENTRY → TASK_REWRITER → ROUTER → FALLBACK → END")
        print("The workflow correctly handles out-of-scope queries!")

        return final_state

    except Exception as e:
        print(f"\n✗ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    try:
        test_workflow_with_fallback()

        print("\n" + "="*60)
        print("INTEGRATION TEST PASSED ✓")
        print("="*60)
        print("\nLe workflow complet avec fallback fonctionne correctement !")
        print("Une requête hors-scope ('c'est quoi la météo ?') est:")
        print("  1. Reformulée par le task_rewriter")
        print("  2. Routée vers fallback_agent par le router")
        print("  3. Traitée par le fallback_node")
        print("  4. Retourne un message d'aide à l'utilisateur")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
