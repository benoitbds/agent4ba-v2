"""Script de test pour valider le refactoring du graph avec RegistryService.

Ce script teste que le workflow charge correctement la configuration
depuis agent_registry.yaml et route les intentions vers les bons agents.

Usage:
    poetry run python test_graph_refactoring.py
"""

import sys


def test_graph_import():
    """Test 1 : Vérifier que le graph se charge sans erreur."""
    print("=" * 70)
    print("TEST 1 : Import du module graph")
    print("=" * 70)

    try:
        from agent4ba.ai import graph

        print("\n✓ Module graph importé avec succès")
        print(f"  - Registre chargé avec {len(graph.INTENT_CONFIG_MAP)} intentions")
        print(f"  - Intentions disponibles : {list(graph.INTENT_CONFIG_MAP.keys())}")
        return graph
    except Exception as e:
        print(f"\n✗ Erreur lors de l'import du graph : {e}")
        raise


def test_intent_mapping(graph):
    """Test 2 : Vérifier le mapping des intentions."""
    print("\n" + "=" * 70)
    print("TEST 2 : Vérification du mapping des intentions")
    print("=" * 70)

    # Intentions attendues
    expected_intents = [
        "decompose_objective",
        "extract_features_from_docs",
        "review_backlog_quality",
        "improve_item_description",
    ]

    for intent_id in expected_intents:
        config = graph.INTENT_CONFIG_MAP.get(intent_id)
        if config:
            print(f"\n✓ {intent_id}:")
            print(f"  - Agent: {config.agent_id}")
            print(f"  - Task: {config.agent_task}")
            print(f"  - Status: {config.status or 'implemented'}")
        else:
            print(f"\n✗ {intent_id} non trouvé dans le mapping")
            raise ValueError(f"Intent {intent_id} manquant")


def test_router_logic(graph):
    """Test 3 : Tester la logique du router_node."""
    print("\n" + "=" * 70)
    print("TEST 3 : Test de la logique du router_node")
    print("=" * 70)

    # Simuler un état avec une intention
    test_state = {
        "intent": {
            "intent_id": "decompose_objective",
            "confidence": 0.95,
            "args": {"objective": "Test objective"},
        }
    }

    result = graph.router_node(test_state)

    print(f"\n✓ Router result:")
    print(f"  - next_node: {result.get('next_node')}")
    print(f"  - agent_id: {result.get('agent_id')}")
    print(f"  - agent_task: {result.get('agent_task')}")

    # Vérifications
    assert result.get("next_node") == "agent", "Le router devrait router vers 'agent'"
    assert result.get("agent_id") == "backlog_agent", "L'agent devrait être 'backlog_agent'"
    assert (
        result.get("agent_task") == "decompose_objective"
    ), "La tâche devrait être 'decompose_objective'"

    print("\n✓ Le router fonctionne correctement")


def test_not_implemented_intent(graph):
    """Test 4 : Tester les intentions not_implemented."""
    print("\n" + "=" * 70)
    print("TEST 4 : Test des intentions not_implemented")
    print("=" * 70)

    # Trouver une intention not_implemented
    not_implemented_intent = None
    for intent_id, config in graph.INTENT_CONFIG_MAP.items():
        if config.status == "not_implemented":
            not_implemented_intent = intent_id
            break

    if not_implemented_intent:
        test_state = {
            "intent": {
                "intent_id": not_implemented_intent,
                "confidence": 0.95,
                "args": {},
            }
        }

        result = graph.router_node(test_state)

        print(f"\n✓ Intent not_implemented : {not_implemented_intent}")
        print(f"  - next_node: {result.get('next_node')}")
        print(f"  - result: {result.get('result')}")

        assert (
            result.get("next_node") == "end"
        ), "Les intentions not_implemented doivent router vers 'end'"
        print("\n✓ Les intentions not_implemented sont correctement gérées")
    else:
        print("\n⚠ Aucune intention not_implemented trouvée pour tester")


def test_low_confidence(graph):
    """Test 5 : Tester la gestion des faibles scores de confiance."""
    print("\n" + "=" * 70)
    print("TEST 5 : Test de la gestion des faibles scores de confiance")
    print("=" * 70)

    test_state = {
        "intent": {
            "intent_id": "decompose_objective",
            "confidence": 0.5,  # Faible confiance
            "args": {},
        }
    }

    result = graph.router_node(test_state)

    print(f"\n✓ Router result avec faible confiance:")
    print(f"  - next_node: {result.get('next_node')}")
    print(f"  - result: {result.get('result')}")

    assert (
        result.get("next_node") == "end"
    ), "Une faible confiance devrait router vers 'end'"
    print("\n✓ La gestion des faibles scores de confiance fonctionne")


def main():
    """Point d'entrée principal du script de test."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "TEST DU REFACTORING DU GRAPH" + " " * 20 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    try:
        # Test 1 : Import
        graph_module = test_graph_import()

        # Test 2 : Mapping
        test_intent_mapping(graph_module)

        # Test 3 : Router logic
        test_router_logic(graph_module)

        # Test 4 : Not implemented
        test_not_implemented_intent(graph_module)

        # Test 5 : Low confidence
        test_low_confidence(graph_module)

        print("\n" + "=" * 70)
        print("✅ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS")
        print("=" * 70)
        print()
        print("Le refactoring du graph fonctionne correctement.")
        print("La configuration est chargée depuis agent_registry.yaml")
        print("et le routage des intentions utilise bien le RegistryService.")
        print()

        return 0

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ERREUR DURANT LES TESTS")
        print("=" * 70)
        print(f"\n{type(e).__name__}: {e}")
        print()
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
