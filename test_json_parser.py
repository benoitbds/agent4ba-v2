#!/usr/bin/env python3
"""
Tests complets pour l'utilitaire de parsing JSON robuste.

Valide que extract_and_parse_json gère correctement tous les formats
de réponse LLM possibles.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from agent4ba.utils.json_parser import JSONParsingError, extract_and_parse_json


def test_case(name: str, input_text: str, expected_output: dict | list = None, should_fail: bool = False):
    """
    Teste un cas d'usage de l'utilitaire de parsing JSON.

    Args:
        name: Nom descriptif du test
        input_text: Texte à parser
        expected_output: Résultat attendu (si should_fail=False)
        should_fail: True si on s'attend à une exception
    """
    print(f"\n{'=' * 80}")
    print(f"TEST: {name}")
    print(f"{'=' * 80}")
    print(f"\n📝 Input ({len(input_text)} chars):")
    print(f"{input_text[:200]}{'...' if len(input_text) > 200 else ''}\n")

    try:
        result = extract_and_parse_json(input_text)

        if should_fail:
            print(f"❌ ÉCHEC: Devrait lever JSONParsingError mais a retourné: {result}")
            return False
        else:
            print(f"✅ Parsing réussi!")
            print(f"📊 Type: {type(result).__name__}")
            print(f"📊 Contenu: {result}")

            if expected_output is not None:
                if result == expected_output:
                    print(f"✅ Résultat correspond à l'attendu")
                    return True
                else:
                    print(f"❌ ÉCHEC: Résultat différent de l'attendu")
                    print(f"   Attendu: {expected_output}")
                    print(f"   Obtenu:  {result}")
                    return False
            return True

    except JSONParsingError as e:
        if should_fail:
            print(f"✅ JSONParsingError levée comme attendu:")
            print(f"   {e}")
            return True
        else:
            print(f"❌ ÉCHEC: JSONParsingError inattendue:")
            print(f"   {e}")
            return False
    except Exception as e:
        print(f"❌ ÉCHEC: Exception inattendue: {type(e).__name__}: {e}")
        return False


def main():
    """Exécute tous les tests."""
    print("\n" + "=" * 80)
    print("🧪 TESTS DE L'UTILITAIRE DE PARSING JSON ROBUSTE")
    print("=" * 80)

    results = []

    # ===== CAS 1: JSON pur (sans balises) =====
    results.append(test_case(
        "Cas 1: JSON objet pur",
        '{"key": "value", "number": 42}',
        expected_output={"key": "value", "number": 42}
    ))

    results.append(test_case(
        "Cas 1b: JSON array pur",
        '[{"type": "feature", "title": "Feature 1"}, {"type": "feature", "title": "Feature 2"}]',
        expected_output=[
            {"type": "feature", "title": "Feature 1"},
            {"type": "feature", "title": "Feature 2"}
        ]
    ))

    # ===== CAS 2: JSON avec balises markdown ```json =====
    results.append(test_case(
        "Cas 2: JSON dans balises ```json",
        '''```json
{
  "key": "value",
  "nested": {
    "data": [1, 2, 3]
  }
}
```''',
        expected_output={"key": "value", "nested": {"data": [1, 2, 3]}}
    ))

    results.append(test_case(
        "Cas 2b: Array dans balises ```json",
        '''```json
[
  {"type": "feature", "title": "Auth"},
  {"type": "feature", "title": "Payment"}
]
```''',
        expected_output=[
            {"type": "feature", "title": "Auth"},
            {"type": "feature", "title": "Payment"}
        ]
    ))

    # ===== CAS 3: JSON avec balises markdown ``` (sans 'json') =====
    results.append(test_case(
        "Cas 3: JSON dans balises ``` génériques",
        '''Voici le résultat:
```
{
  "status": "success",
  "data": {"items": [1, 2, 3]}
}
```
C'est tout!''',
        expected_output={"status": "success", "data": {"items": [1, 2, 3]}}
    ))

    # ===== CAS 4: JSON nu avec texte avant/après =====
    results.append(test_case(
        "Cas 4: JSON nu avec texte avant et après",
        '''Voici la réponse que vous avez demandée:

{
  "features": [
    {"title": "Feature 1"},
    {"title": "Feature 2"}
  ]
}

J'espère que cela répond à votre question!''',
        expected_output={
            "features": [
                {"title": "Feature 1"},
                {"title": "Feature 2"}
            ]
        }
    ))

    results.append(test_case(
        "Cas 4b: Array nu avec texte avant",
        '''Here are the items:
[
  {"id": 1, "name": "Item 1"},
  {"id": 2, "name": "Item 2"}
]''',
        expected_output=[
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ]
    ))

    # ===== CAS 5: Texte sans JSON (doit échouer) =====
    results.append(test_case(
        "Cas 5: Texte sans JSON valide",
        "Ceci est juste du texte sans aucun JSON. Il n'y a pas de structure de données ici.",
        should_fail=True
    ))

    results.append(test_case(
        "Cas 5b: Chaîne vide",
        "",
        should_fail=True
    ))

    results.append(test_case(
        "Cas 5c: Whitespace uniquement",
        "   \n\t  \n  ",
        should_fail=True
    ))

    # ===== CAS 6: JSON malformé (doit échouer) =====
    results.append(test_case(
        "Cas 6: JSON malformé dans balises",
        '''```json
{
  "key": "value",
  "missing_closing_brace": "oops"
```''',
        should_fail=True
    ))

    results.append(test_case(
        "Cas 6b: JSON avec virgule finale (techniquement invalide)",
        '''{
  "key": "value",
  "items": [1, 2, 3,],
}''',
        should_fail=True
    ))

    # ===== CAS 7: JSON avec caractères d'échappement =====
    results.append(test_case(
        "Cas 7: JSON avec caractères échappés",
        '''{"message": "Hello\\nWorld", "path": "C:\\\\Users\\\\test"}''',
        expected_output={"message": "Hello\nWorld", "path": "C:\\Users\\test"}
    ))

    # ===== CAS 8: JSON multilignes complexe =====
    results.append(test_case(
        "Cas 8: JSON complexe multilignes",
        '''Voici la liste des features:
```json
[
  {
    "type": "feature",
    "title": "User Authentication",
    "description": "Secure login system",
    "attributes": {
      "priority": "high",
      "points": 8
    }
  },
  {
    "type": "feature",
    "title": "Shopping Cart",
    "description": "Add/remove items",
    "attributes": {
      "priority": "medium",
      "points": 5
    }
  }
]
```
''',
        expected_output=[
            {
                "type": "feature",
                "title": "User Authentication",
                "description": "Secure login system",
                "attributes": {"priority": "high", "points": 8}
            },
            {
                "type": "feature",
                "title": "Shopping Cart",
                "description": "Add/remove items",
                "attributes": {"priority": "medium", "points": 5}
            }
        ]
    ))

    # ===== RÉSUMÉ =====
    print("\n\n" + "=" * 80)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 80)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    for i, (success, name) in enumerate(zip(results, [
        "Cas 1: JSON objet pur",
        "Cas 1b: JSON array pur",
        "Cas 2: JSON dans balises ```json",
        "Cas 2b: Array dans balises ```json",
        "Cas 3: JSON dans balises ``` génériques",
        "Cas 4: JSON nu avec texte avant et après",
        "Cas 4b: Array nu avec texte avant",
        "Cas 5: Texte sans JSON valide",
        "Cas 5b: Chaîne vide",
        "Cas 5c: Whitespace uniquement",
        "Cas 6: JSON malformé dans balises",
        "Cas 6b: JSON avec virgule finale",
        "Cas 7: JSON avec caractères échappés",
        "Cas 8: JSON complexe multilignes",
    ]), 1):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{i}. {name}: {status}")

    print(f"\n{'=' * 80}")
    print(f"TOTAL: {passed}/{total} tests réussis ({failed} échecs)")
    print(f"{'=' * 80}\n")

    if failed == 0:
        print("✅ Tous les tests passent ! L'utilitaire est robuste et prêt pour production.")
    else:
        print(f"❌ {failed} test(s) ont échoué. Vérifier l'implémentation.")

    # Retourner un code de sortie approprié
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
