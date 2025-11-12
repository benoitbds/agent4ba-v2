#!/usr/bin/env python3
"""Test script pour la fonctionnalité de suppression de documents."""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent))

from agent4ba.core.document_ingestion import DocumentIngestionService


def test_delete_document():
    """Teste la suppression d'un document."""
    print("🧪 Test de suppression de document...")

    project_id = "test-project"
    document_name = "test-doc.txt"

    # Créer une instance du service
    service = DocumentIngestionService(project_id)

    # Vérifier que le document existe
    doc_path = service.documents_dir / document_name
    print(f"📄 Vérification de l'existence du document: {doc_path}")

    if not doc_path.exists():
        print(f"❌ Le document {document_name} n'existe pas!")
        return False

    print(f"✅ Le document existe")

    # Tester la suppression
    try:
        result = service.delete_document(document_name)
        print(f"✅ Suppression réussie!")
        print(f"   Status: {result['status']}")
        print(f"   Document: {result['document_name']}")
        print(f"   Vecteurs supprimés: {result['vectors_deleted']}")
        print(f"   Message: {result['message']}")

        # Vérifier que le fichier a été supprimé
        if doc_path.exists():
            print(f"❌ Le fichier existe encore après suppression!")
            return False

        print(f"✅ Le fichier a bien été supprimé du disque")
        return True

    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_nonexistent_document():
    """Teste la suppression d'un document qui n'existe pas."""
    print("\n🧪 Test de suppression d'un document inexistant...")

    project_id = "test-project"
    document_name = "nonexistent-doc.txt"

    service = DocumentIngestionService(project_id)

    try:
        result = service.delete_document(document_name)
        print(f"❌ La suppression aurait dû échouer mais a réussi!")
        return False
    except FileNotFoundError as e:
        print(f"✅ FileNotFoundError levée comme attendu: {e}")
        return True
    except Exception as e:
        print(f"❌ Mauvais type d'exception levée: {type(e).__name__}: {e}")
        return False


def test_delete_with_path_traversal():
    """Teste la validation contre les attaques path traversal."""
    print("\n🧪 Test de validation contre path traversal...")

    project_id = "test-project"
    malicious_names = [
        "../../../etc/passwd",
        "../../test.txt",
        "/etc/passwd",
        "test/../../../etc/passwd"
    ]

    service = DocumentIngestionService(project_id)

    all_passed = True
    for malicious_name in malicious_names:
        try:
            result = service.delete_document(malicious_name)
            print(f"❌ La validation aurait dû rejeter: {malicious_name}")
            all_passed = False
        except ValueError as e:
            print(f"✅ Rejeté comme attendu: {malicious_name}")
        except Exception as e:
            print(f"⚠️  Exception inattendue pour {malicious_name}: {type(e).__name__}: {e}")
            all_passed = False

    return all_passed


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Tests de la fonctionnalité de suppression de documents")
    print("=" * 60)

    # Test 1: Suppression normale
    test1_passed = test_delete_document()

    # Test 2: Document inexistant
    test2_passed = test_delete_nonexistent_document()

    # Test 3: Path traversal
    test3_passed = test_delete_with_path_traversal()

    print("\n" + "=" * 60)
    print("📊 Résultats des tests:")
    print(f"   Test 1 (suppression normale): {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Test 2 (document inexistant): {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"   Test 3 (path traversal): {'✅ PASS' if test3_passed else '❌ FAIL'}")

    all_passed = test1_passed and test2_passed and test3_passed
    print(f"\n   Résultat global: {'✅ TOUS LES TESTS RÉUSSIS' if all_passed else '❌ CERTAINS TESTS ONT ÉCHOUÉ'}")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)
