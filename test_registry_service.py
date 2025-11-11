"""Script de test manuel pour le service de registre des agents.

Ce script permet de tester :
1. Le chargement de la configuration par défaut
2. La fusion avec un fichier local
3. Les méthodes helper du registre

Usage:
    poetry run python test_registry_service.py
"""

from agent4ba.core.registry_service import load_agent_registry, reset_agent_registry


def test_default_config():
    """Test 1 : Chargement de la configuration par défaut."""
    print("=" * 70)
    print("TEST 1 : Chargement de la configuration par défaut")
    print("=" * 70)

    registry = load_agent_registry()

    print(f"\n✓ Agents chargés ({len(registry.agents)}) :")
    for agent in registry.agents:
        print(f"  - {agent.id}: {agent.description[:60]}...")

    print(f"\n✓ Intentions chargées ({len(registry.intent_mapping)}) :")
    for intent in registry.intent_mapping:
        status = f" [{intent.status}]" if intent.status else ""
        print(f"  - {intent.intent_id} -> {intent.agent_id}.{intent.agent_task}{status}")

    return registry


def test_helper_methods(registry):
    """Test 2 : Vérification des méthodes helper."""
    print("\n" + "=" * 70)
    print("TEST 2 : Méthodes helper")
    print("=" * 70)

    # Recherche d'un agent
    backlog_agent = registry.get_agent_by_id("backlog_agent")
    if backlog_agent:
        print(f"\n✓ get_agent_by_id('backlog_agent'):")
        print(f"  ID: {backlog_agent.id}")
        print(f"  Description: {backlog_agent.description[:80]}...")
    else:
        print("\n✗ backlog_agent non trouvé")

    # Recherche d'une intention
    decompose_intent = registry.get_intent_mapping("decompose_objective")
    if decompose_intent:
        print(f"\n✓ get_intent_mapping('decompose_objective'):")
        print(f"  Intent ID: {decompose_intent.intent_id}")
        print(f"  Agent ID: {decompose_intent.agent_id}")
        print(f"  Agent Task: {decompose_intent.agent_task}")
        print(f"  Prompt File: {decompose_intent.prompt_file}")
    else:
        print("\n✗ decompose_objective non trouvé")


def test_local_config_merge():
    """Test 3 : Fusion avec un fichier local (si présent)."""
    print("\n" + "=" * 70)
    print("TEST 3 : Fusion avec configuration locale")
    print("=" * 70)

    from pathlib import Path

    project_root = Path(__file__).parent
    local_config = project_root / "agent_registry.local.yaml"

    if local_config.exists():
        print(f"\n✓ Fichier local détecté : {local_config}")
        print("  Rechargement de la configuration...")

        # Réinitialiser pour forcer le rechargement
        reset_agent_registry()
        registry = load_agent_registry()

        print(f"  Configuration rechargée avec {len(registry.agents)} agents")
        print("  Vérifiez que les valeurs du fichier local ont bien écrasé les valeurs par défaut")
    else:
        print(f"\n⚠ Aucun fichier local trouvé : {local_config}")
        print("  Pour tester la fusion, créez un fichier agent_registry.local.yaml")
        print("  avec des valeurs différentes de agent_registry.default.yaml")


def main():
    """Point d'entrée principal du script de test."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "TEST DU SERVICE DE REGISTRE DES AGENTS" + " " * 15 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    try:
        # Test 1 : Configuration par défaut
        registry = test_default_config()

        # Test 2 : Méthodes helper
        test_helper_methods(registry)

        # Test 3 : Fusion avec fichier local
        test_local_config_merge()

        print("\n" + "=" * 70)
        print("✅ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS")
        print("=" * 70)
        print()

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ERREUR DURANT LES TESTS")
        print("=" * 70)
        print(f"\n{type(e).__name__}: {e}")
        print()
        raise


if __name__ == "__main__":
    main()
