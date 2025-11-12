"""Test unitaire pour la génération d'ID séquentiels."""

from agent4ba.core.models import WorkItem
from agent4ba.core.workitem_utils import (
    assign_sequential_ids,
    generate_project_prefix,
    get_next_sequential_index,
)


def test_generate_project_prefix():
    """Teste la génération de préfixes de projet."""
    print("\n=== Test: generate_project_prefix ===")

    test_cases = [
        ("recette-mvp", "REC"),
        ("mon-projet-test", "MON"),
        ("ab-test", "AB"),
        ("project", "PRO"),
        ("a", "AX"),  # Un seul caractère, complété avec X
        ("test_project", "TES"),
        ("123-test", "TES"),  # Commence par des chiffres
    ]

    for project_id, expected_prefix in test_cases:
        result = generate_project_prefix(project_id)
        status = "✓" if result == expected_prefix else "✗"
        print(f"{status} {project_id} -> {result} (expected: {expected_prefix})")
        if result != expected_prefix:
            print(f"  ERROR: Expected {expected_prefix}, got {result}")


def test_get_next_sequential_index():
    """Teste la récupération du prochain index séquentiel."""
    print("\n=== Test: get_next_sequential_index ===")

    # Test 1: Projet vide (aucun item)
    print("\nTest 1: Projet vide")
    prefix, next_index = get_next_sequential_index("mon-projet-test", [])
    print(f"  Prefix: {prefix}, Next index: {next_index}")
    assert prefix == "MON", f"Expected prefix 'MON', got '{prefix}'"
    assert next_index == 1, f"Expected next_index 1, got {next_index}"
    print("  ✓ PASS")

    # Test 2: Projet avec des items existants
    print("\nTest 2: Projet avec items existants")
    existing_items = [
        WorkItem(
            id="MON-1",
            project_id="mon-projet-test",
            type="feature",
            title="Feature 1",
        ),
        WorkItem(
            id="MON-3",
            project_id="mon-projet-test",
            type="story",
            title="Story 1",
        ),
        WorkItem(
            id="MON-2",
            project_id="mon-projet-test",
            type="story",
            title="Story 2",
        ),
    ]
    prefix, next_index = get_next_sequential_index("mon-projet-test", existing_items)
    print(f"  Prefix: {prefix}, Next index: {next_index}")
    assert prefix == "MON", f"Expected prefix 'MON', got '{prefix}'"
    assert next_index == 4, f"Expected next_index 4, got {next_index}"
    print("  ✓ PASS")

    # Test 3: Mélange avec d'anciens ID temp
    print("\nTest 3: Mélange d'ID séquentiels et temporaires")
    mixed_items = [
        WorkItem(
            id="REC-1",
            project_id="recette-mvp",
            type="feature",
            title="Feature 1",
        ),
        WorkItem(
            id="temp-5",
            project_id="recette-mvp",
            type="story",
            title="Story temp",
        ),
        WorkItem(
            id="REC-2",
            project_id="recette-mvp",
            type="story",
            title="Story 2",
        ),
    ]
    prefix, next_index = get_next_sequential_index("recette-mvp", mixed_items)
    print(f"  Prefix: {prefix}, Next index: {next_index}")
    assert prefix == "REC", f"Expected prefix 'REC', got '{prefix}'"
    assert next_index == 3, f"Expected next_index 3, got {next_index}"
    print("  ✓ PASS (temp-5 ignoré, seuls REC-1 et REC-2 comptent)")


def test_assign_sequential_ids():
    """Teste l'assignation d'ID séquentiels."""
    print("\n=== Test: assign_sequential_ids ===")

    # Test 1: Nouveaux items sur projet vide
    print("\nTest 1: Nouveaux items sur projet vide")
    new_items = [
        {"id": "temp-1", "title": "Feature 1", "type": "feature"},
        {"id": "temp-2", "title": "Story 1", "type": "story"},
        {"id": "temp-3", "title": "Story 2", "type": "story"},
    ]
    result = assign_sequential_ids("mon-projet-test", [], new_items)
    print(f"  Generated IDs: {[item['id'] for item in result]}")
    assert result[0]["id"] == "MON-1", f"Expected 'MON-1', got '{result[0]['id']}'"
    assert result[1]["id"] == "MON-2", f"Expected 'MON-2', got '{result[1]['id']}'"
    assert result[2]["id"] == "MON-3", f"Expected 'MON-3', got '{result[2]['id']}'"
    print("  ✓ PASS")

    # Test 2: Nouveaux items avec des items existants
    print("\nTest 2: Continuation de la séquence")
    existing_items = [
        WorkItem(
            id="REC-1",
            project_id="recette-mvp",
            type="feature",
            title="Feature 1",
        ),
        WorkItem(
            id="REC-2",
            project_id="recette-mvp",
            type="story",
            title="Story 1",
        ),
    ]
    new_items = [
        {"id": "temp-1", "title": "New Feature", "type": "feature"},
        {"id": "temp-2", "title": "New Story", "type": "story"},
    ]
    result = assign_sequential_ids("recette-mvp", existing_items, new_items)
    print(f"  Generated IDs: {[item['id'] for item in result]}")
    assert result[0]["id"] == "REC-3", f"Expected 'REC-3', got '{result[0]['id']}'"
    assert result[1]["id"] == "REC-4", f"Expected 'REC-4', got '{result[1]['id']}'"
    print("  ✓ PASS (continue depuis REC-2)")


def main():
    """Exécute tous les tests."""
    print("=" * 80)
    print("Tests unitaires pour la génération d'ID séquentiels")
    print("=" * 80)

    try:
        test_generate_project_prefix()
        test_get_next_sequential_index()
        test_assign_sequential_ids()

        print("\n" + "=" * 80)
        print("✓ TOUS LES TESTS SONT PASSÉS !")
        print("=" * 80)
        return 0

    except AssertionError as e:
        print("\n" + "=" * 80)
        print(f"✗ TEST ÉCHOUÉ: {e}")
        print("=" * 80)
        return 1
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"✗ ERREUR INATTENDUE: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
