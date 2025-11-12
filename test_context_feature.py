#!/usr/bin/env python3
"""
Script de test pour la fonctionnalité de contexte dans /chat.

Ce script démontre comment utiliser le nouveau champ 'context' pour cibler
des documents ou work items spécifiques dans les requêtes.
"""

import requests

# Configuration
API_BASE_URL = "http://localhost:8000"
PROJECT_ID = "demo"

def test_without_context():
    """Test 1: Requête normale sans contexte."""
    print("\n=== Test 1: Requête sans contexte ===")

    payload = {
        "project_id": PROJECT_ID,
        "query": "Quelles sont les principales fonctionnalités décrites dans les documents ?",
    }

    print(f"Payload: {payload}")
    print("Comportement attendu: Recherche dans TOUS les documents du projet")
    return payload


def test_with_document_context():
    """Test 2: Requête avec contexte document."""
    print("\n=== Test 2: Requête avec contexte document ===")

    payload = {
        "project_id": PROJECT_ID,
        "query": "Quelles sont les principales fonctionnalités décrites ?",
        "context": [
            {
                "type": "document",
                "id": "document1.pdf"  # Nom du fichier uploadé
            }
        ]
    }

    print(f"Payload: {payload}")
    print("Comportement attendu: Recherche UNIQUEMENT dans document1.pdf")
    return payload


def test_with_work_item_context():
    """Test 3: Requête avec contexte work_item."""
    print("\n=== Test 3: Requête avec contexte work_item ===")

    payload = {
        "project_id": PROJECT_ID,
        "query": "Améliore la description de ce work item",
        "context": [
            {
                "type": "work_item",
                "id": "temp-1"  # ID du work item
            }
        ]
    }

    print(f"Payload: {payload}")
    print("Comportement attendu: Améliore la description du work item temp-1")
    print("Note: Le context est prioritaire sur l'ID détecté dans la query")
    return payload


def test_with_multiple_contexts():
    """Test 4: Requête avec plusieurs éléments de contexte."""
    print("\n=== Test 4: Requête avec contextes multiples ===")

    payload = {
        "project_id": PROJECT_ID,
        "query": "Analyse ces éléments",
        "context": [
            {
                "type": "document",
                "id": "document1.pdf"
            },
            {
                "type": "document",
                "id": "document2.pdf"
            }
        ]
    }

    print(f"Payload: {payload}")
    print("Comportement attendu: Recherche dans document1.pdf ET document2.pdf")
    print("Note: Actuellement seul le premier élément de chaque type est utilisé")
    return payload


def main():
    """Affiche les exemples de test."""
    print("=" * 70)
    print("TESTS DE LA FONCTIONNALITÉ DE CONTEXTE")
    print("=" * 70)

    print("\nCe script illustre comment utiliser le nouveau champ 'context'")
    print("dans les requêtes /chat pour cibler des documents ou work items.")

    # Afficher tous les tests
    test_without_context()
    test_with_document_context()
    test_with_work_item_context()
    test_with_multiple_contexts()

    print("\n" + "=" * 70)
    print("UTILISATION")
    print("=" * 70)
    print("\nPour tester avec curl:")
    print("\ncurl -X POST http://localhost:8000/chat \\")
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{\n    "project_id": "demo",')
    print('    "query": "Analyse ce document",')
    print('    "context": [{"type": "document", "id": "document1.pdf"}]')
    print("  }'")

    print("\nPour tester via Swagger UI:")
    print("1. Ouvrir http://localhost:8000/docs")
    print("2. Aller à l'endpoint POST /chat")
    print("3. Cliquer sur 'Try it out'")
    print("4. Ajouter le champ 'context' dans le JSON de la requête")

    print("\n" + "=" * 70)
    print("COMPATIBILITÉ")
    print("=" * 70)
    print("\n✓ Le champ 'context' est OPTIONNEL")
    print("✓ Les anciennes requêtes sans 'context' fonctionnent toujours")
    print("✓ Si 'context' est null ou [], le comportement est inchangé")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
