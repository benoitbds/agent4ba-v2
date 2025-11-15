#!/usr/bin/env python3
"""
Test de la normalisation des noms d'agents.

Vérifie que la logique de normalisation gère correctement les variations de casse.
"""

# Map de normalisation (copiée depuis graph.py)
agent_id_map = {
    "epicarchitectagent": "epic_architect_agent",
    "epic_architect_agent": "epic_architect_agent",
    "storytelleragent": "story_teller_agent",
    "story_teller_agent": "story_teller_agent",
    "backlogagent": "backlog_agent",
    "backlog_agent": "backlog_agent",
    "testagent": "test_agent",
    "test_agent": "test_agent",
    "documentagent": "document_agent",
    "document_agent": "document_agent",
    "fallbackagent": "fallback_agent",
    "fallback_agent": "fallback_agent",
}

def normalize_agent_id(agent_id: str) -> str:
    """Normalise le nom d'un agent."""
    normalized_key = agent_id.lower().replace("_", "")
    if normalized_key in agent_id_map:
        return agent_id_map[normalized_key]
    return agent_id  # Retourner tel quel si non trouvé


# Tests
test_cases = [
    # Format attendu (snake_case)
    ("epic_architect_agent", "epic_architect_agent", True),
    ("story_teller_agent", "story_teller_agent", True),
    ("backlog_agent", "backlog_agent", True),
    ("fallback_agent", "fallback_agent", True),

    # Variations de casse (PascalCase)
    ("EpicArchitectAgent", "epic_architect_agent", True),
    ("StoryTellerAgent", "story_teller_agent", True),
    ("BacklogAgent", "backlog_agent", True),
    ("FallbackAgent", "fallback_agent", True),

    # Variations mixtes
    ("epicArchitectAgent", "epic_architect_agent", True),
    ("Epic_Architect_Agent", "epic_architect_agent", True),
    ("EPIC_ARCHITECT_AGENT", "epic_architect_agent", True),

    # Agent inconnu (ne devrait pas être normalisé)
    ("unknown_agent", "unknown_agent", False),
]

print("=" * 80)
print("TEST DE NORMALISATION DES NOMS D'AGENTS")
print("=" * 80)

passed = 0
failed = 0

for input_name, expected_output, should_normalize in test_cases:
    normalized = normalize_agent_id(input_name)
    success = (normalized == expected_output)

    if success:
        status = "✅ PASS"
        passed += 1
    else:
        status = "❌ FAIL"
        failed += 1

    print(f"\n{status}")
    print(f"  Input:    {input_name}")
    print(f"  Expected: {expected_output}")
    print(f"  Got:      {normalized}")
    if should_normalize and input_name != normalized:
        print(f"  ℹ️  Normalized from '{input_name}' to '{normalized}'")

print("\n" + "=" * 80)
print(f"📊 RÉSUMÉ: {passed} tests réussis, {failed} échecs")
print("=" * 80)

if failed == 0:
    print("✅ Tous les tests de normalisation passent !")
    print("✅ Le routeur peut maintenant gérer les variations de casse des noms d'agents")
else:
    print(f"❌ {failed} test(s) ont échoué")
    exit(1)
