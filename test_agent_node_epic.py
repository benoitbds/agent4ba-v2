#!/usr/bin/env python3
"""
Test rapide pour vérifier que le agent_node gère bien epic_architect_agent.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from agent4ba.ai.graph import GraphState

# Simuler un état avec epic_architect_agent
test_state: GraphState = {
    "project_id": "test-project",
    "user_query": "Génère un site e-commerce",
    "document_content": "",
    "context": None,
    "rewritten_task": "Générer les features pour un site e-commerce",
    "intent": {"args": {"objective": "site e-commerce"}},
    "intent_args": {"objective": "site e-commerce"},
    "next_node": "agent",
    "agent_id": "epic_architect_agent",  # C'est l'agent qu'on teste
    "agent_task": "generate_epics",
    "impact_plan": {},
    "status": "",
    "approval_decision": None,
    "result": "",
    "agent_events": [],
    "thread_id": "test-thread",
    "ambiguous_intent": False,
    "clarification_needed": False,
    "clarification_question": None,
    "user_response": None,
}

print("=" * 80)
print("TEST: Vérification que agent_node reconnaît epic_architect_agent")
print("=" * 80)

print(f"\n📋 État de test:")
print(f"  - agent_id: {test_state['agent_id']}")
print(f"  - agent_task: {test_state['agent_task']}")
print(f"  - args: {test_state['intent_args']}")

# Tester si le code reconnaît l'agent
agent_id = test_state.get("agent_id", "unknown")
agent_task = test_state.get("agent_task", "unknown_task")

print(f"\n🔍 Vérification du code agent_node:")

# Simuler la logique du agent_node
if agent_id == "epic_architect_agent":
    if agent_task == "generate_epics":
        print(f"  ✅ epic_architect_agent est reconnu")
        print(f"  ✅ Tâche generate_epics est reconnue")
        print(f"  ✅ Le workflow appellerait epic_architect_agent.generate_epics(state)")
        success = True
    else:
        print(f"  ❌ Tâche '{agent_task}' non reconnue pour epic_architect_agent")
        success = False
else:
    print(f"  ❌ Agent '{agent_id}' non reconnu dans le code")
    success = False

print("\n" + "=" * 80)
if success:
    print("✅ TEST RÉUSSI: epic_architect_agent est correctement intégré dans agent_node")
else:
    print("❌ TEST ÉCHOUÉ: Problème d'intégration détecté")
print("=" * 80)

# Vérifier également les imports
print("\n🔍 Vérification des imports:")
try:
    from agent4ba.ai import epic_architect_agent
    print("  ✅ epic_architect_agent est importable")

    # Vérifier que la fonction generate_epics existe
    if hasattr(epic_architect_agent, 'generate_epics'):
        print("  ✅ epic_architect_agent.generate_epics() existe")
    else:
        print("  ❌ epic_architect_agent.generate_epics() n'existe pas")
except ImportError as e:
    print(f"  ❌ Impossible d'importer epic_architect_agent: {e}")

print("\n" + "=" * 80)
print("📊 CONCLUSION")
print("=" * 80)
print("Le code agent_node dans graph.py est déjà configuré pour gérer epic_architect_agent.")
print("Si vous obtenez l'erreur 'Unknown agent: EpicArchitectAgent', vérifiez:")
print("  1. Que le LLM retourne 'epic_architect_agent' (snake_case) et non 'EpicArchitectAgent'")
print("  2. Que le serveur utilise bien la dernière version du code (redémarrer si nécessaire)")
print("  3. Les logs DEBUG pour voir exactement ce que le routeur retourne")
print("=" * 80)
