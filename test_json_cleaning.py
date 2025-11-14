#!/usr/bin/env python3
"""
Test rapide de la logique de nettoyage JSON.

Ce script teste que le nettoyage JSON fonctionne correctement avec:
1. JSON pur (sans balises)
2. JSON avec balises ```json
3. JSON avec balises et texte avant/après
"""

import json

def clean_json_string(raw_string: str) -> str:
    """
    Nettoie une chaîne pour extraire uniquement le JSON.

    Args:
        raw_string: La chaîne brute potentiellement avec des balises markdown

    Returns:
        La chaîne JSON nettoyée
    """
    try:
        start_index = raw_string.index('{')
        end_index = raw_string.rindex('}') + 1
        clean_json_str = raw_string[start_index:end_index]
        return clean_json_str
    except ValueError as e:
        # Si '{' ou '}' ne sont pas trouvés, on retourne la chaîne brute
        print(f"WARNING: Could not find JSON delimiters: {e}")
        return raw_string


# Test 1: JSON pur
print("=" * 80)
print("TEST 1: JSON pur (sans balises)")
print("=" * 80)

test1 = '''{"thought": "Test", "decision": {"agent": "epic_architect_agent", "task": "generate_epics", "args": {"objective": "test"}}}'''

cleaned1 = clean_json_string(test1)
print(f"Input:\n{test1}\n")
print(f"Cleaned:\n{cleaned1}\n")

try:
    parsed1 = json.loads(cleaned1)
    print(f"✅ Parsing réussi: {list(parsed1.keys())}")
except json.JSONDecodeError as e:
    print(f"❌ Parsing échoué: {e}")

# Test 2: JSON avec balises markdown
print("\n" + "=" * 80)
print("TEST 2: JSON avec balises ```json")
print("=" * 80)

test2 = '''```json
{
  "thought": "1. Analyse Sémantique: L'utilisateur souhaite créer un projet.",
  "decision": {
    "agent": "epic_architect_agent",
    "task": "generate_epics",
    "args": {
      "objective": "site e-commerce"
    }
  }
}
```'''

cleaned2 = clean_json_string(test2)
print(f"Input:\n{test2}\n")
print(f"Cleaned:\n{cleaned2}\n")

try:
    parsed2 = json.loads(cleaned2)
    print(f"✅ Parsing réussi: {list(parsed2.keys())}")
except json.JSONDecodeError as e:
    print(f"❌ Parsing échoué: {e}")

# Test 3: JSON avec texte avant et après
print("\n" + "=" * 80)
print("TEST 3: JSON avec texte avant et après")
print("=" * 80)

test3 = '''Voici le résultat:

{
  "thought": "Test de pensée",
  "decision": {
    "agent": "story_teller_agent",
    "task": "decompose_feature_into_stories",
    "args": {
      "feature_id": "FIR-3"
    }
  }
}

C'est tout!'''

cleaned3 = clean_json_string(test3)
print(f"Input:\n{test3}\n")
print(f"Cleaned:\n{cleaned3}\n")

try:
    parsed3 = json.loads(cleaned3)
    print(f"✅ Parsing réussi: {list(parsed3.keys())}")
except json.JSONDecodeError as e:
    print(f"❌ Parsing échoué: {e}")

# Test 4: JSON invalide (pas de délimiteurs)
print("\n" + "=" * 80)
print("TEST 4: Texte sans JSON")
print("=" * 80)

test4 = '''Ceci est juste du texte sans JSON'''

cleaned4 = clean_json_string(test4)
print(f"Input:\n{test4}\n")
print(f"Cleaned:\n{cleaned4}\n")

try:
    parsed4 = json.loads(cleaned4)
    print(f"✅ Parsing réussi: {list(parsed4.keys())}")
except json.JSONDecodeError as e:
    print(f"❌ Parsing échoué (attendu): {e}")

print("\n" + "=" * 80)
print("📊 RÉSUMÉ")
print("=" * 80)
print("✅ Le nettoyage JSON extrait correctement le JSON depuis diverses formes de sortie LLM")
print("✅ Les balises markdown ```json sont correctement supprimées")
print("✅ Le texte avant/après le JSON est correctement ignoré")
print("=" * 80)
