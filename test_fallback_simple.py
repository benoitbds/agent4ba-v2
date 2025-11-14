"""Test simple du nœud de fallback sans dépendances externes."""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))


def test_fallback_node():
    """Teste le nœud de fallback directement."""
    from agent4ba.ai.nodes.fallback_node import handle_unknown_intent

    # Simuler un état de graphe
    state = {
        "user_query": "c'est quoi la météo ?",
        "rewritten_task": "Indiquer la météo actuelle",
        "project_id": "test-project",
    }

    print(f"\n{'='*60}")
    print(f"Testing fallback node")
    print(f"Input state:")
    print(f"  User query: {state['user_query']}")
    print(f"  Rewritten task: {state['rewritten_task']}")
    print(f"  Project ID: {state['project_id']}")
    print(f"{'='*60}\n")

    result = handle_unknown_intent(state)

    print(f"Fallback node result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Result message:")
    print(f"  {result.get('result')}")
    print()

    # Vérifications
    assert result.get('status') == 'completed', f"Expected status 'completed', got '{result.get('status')}'"
    assert 'Désolé' in result.get('result', ''), "Expected 'Désolé' in result message"
    assert 'gestion de backlog' in result.get('result', '').lower(), "Expected 'gestion de backlog' in result message"

    return result


def verify_router_prompt():
    """Vérifie que le prompt du routeur contient la règle de fallback."""
    from pathlib import Path

    prompt_path = Path(__file__).parent / "prompts" / "router.yaml"

    print(f"\n{'='*60}")
    print(f"Verifying router prompt configuration")
    print(f"{'='*60}\n")

    with prompt_path.open("r", encoding="utf-8") as f:
        content = f.read()

    # Vérifier la présence de la règle de fallback
    checks = [
        ("fallback_agent", "fallback_agent found in prompt"),
        ("handle_unknown_intent", "handle_unknown_intent found in prompt"),
        ("RÈGLE DE FALLBACK", "Fallback rule section found"),
        ("météo", "Météo example found"),
    ]

    all_checks_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"✓ {description}")
        else:
            print(f"✗ {description} - FAILED")
            all_checks_passed = False

    assert all_checks_passed, "Some checks failed in router prompt"
    print("\n✓ All router prompt checks passed")


def verify_graph_integration():
    """Vérifie que le graphe intègre correctement le nœud de fallback."""
    from pathlib import Path

    graph_path = Path(__file__).parent / "agent4ba" / "ai" / "graph.py"

    print(f"\n{'='*60}")
    print(f"Verifying graph integration")
    print(f"{'='*60}\n")

    with graph_path.open("r", encoding="utf-8") as f:
        content = f.read()

    # Vérifier la présence des éléments nécessaires
    checks = [
        ("from agent4ba.ai.nodes import ask_for_clarification, handle_unknown_intent", "Import of handle_unknown_intent"),
        ('workflow.add_node("fallback", handle_unknown_intent)', "Fallback node added to workflow"),
        ('"fallback": "fallback"', "Fallback route in conditional edges"),
        ('workflow.add_edge("fallback", "end")', "Fallback to end edge"),
        ('agent_id == "fallback_agent"', "Fallback agent check in route_after_router"),
    ]

    all_checks_passed = True
    for check_str, description in checks:
        if check_str in content:
            print(f"✓ {description}")
        else:
            print(f"✗ {description} - FAILED")
            all_checks_passed = False

    assert all_checks_passed, "Some checks failed in graph integration"
    print("\n✓ All graph integration checks passed")


if __name__ == "__main__":
    try:
        # Test 1: Vérifier le prompt du routeur
        verify_router_prompt()

        # Test 2: Vérifier l'intégration dans le graphe
        verify_graph_integration()

        # Test 3: Tester le nœud de fallback
        test_fallback_node()

        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        print("\nLe mécanisme de fallback est correctement implémenté !")
        print("Les requêtes hors-scope seront maintenant gérées proprement.")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
