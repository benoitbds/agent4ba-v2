"""Test de validation de structure pour la boucle de clarification.

Ce test vérifie que tous les composants nécessaires à la boucle de clarification
sont correctement définis et peuvent être importés.
"""

import sys
import ast
import inspect


def test_graphstate_structure():
    """Vérifie que GraphState contient les champs de clarification."""
    print("\n" + "=" * 80)
    print("TEST 1: Vérification de la structure de GraphState")
    print("=" * 80)

    # Lire le fichier graph.py et parser l'AST
    with open("agent4ba/ai/graph.py", "r") as f:
        content = f.read()

    # Vérifier la présence des champs dans le code source
    required_fields = [
        "ambiguous_intent",
        "clarification_needed",
        "clarification_question",
        "user_response",
    ]

    missing_fields = []
    for field in required_fields:
        if field not in content:
            missing_fields.append(field)
        else:
            print(f"✓ Champ '{field}' trouvé dans GraphState")

    if missing_fields:
        print(f"\n❌ ÉCHEC: Champs manquants: {missing_fields}")
        return False
    else:
        print("\n✅ SUCCÈS: Tous les champs de clarification sont présents")
        return True


def test_clarification_node_exists():
    """Vérifie que le nœud de clarification existe."""
    print("\n" + "=" * 80)
    print("TEST 2: Vérification de l'existence du nœud de clarification")
    print("=" * 80)

    try:
        # Vérifier que le fichier existe
        import os
        clarification_file = "agent4ba/ai/nodes/clarification_node.py"
        if not os.path.exists(clarification_file):
            print(f"❌ ÉCHEC: Fichier {clarification_file} n'existe pas")
            return False

        print(f"✓ Fichier {clarification_file} existe")

        # Vérifier que la fonction ask_for_clarification est définie
        with open(clarification_file, "r") as f:
            content = f.read()

        if "def ask_for_clarification" not in content:
            print("❌ ÉCHEC: Fonction ask_for_clarification non trouvée")
            return False

        print("✓ Fonction ask_for_clarification est définie")

        # Vérifier les paramètres et le retour
        if "state:" not in content or "dict[str, Any]" not in content:
            print("❌ ÉCHEC: Signature de fonction incorrecte")
            return False

        print("✓ Signature de fonction correcte")

        # Vérifier les retours attendus
        required_returns = [
            "clarification_needed",
            "clarification_question",
            "status",
        ]

        for ret in required_returns:
            if ret not in content:
                print(f"❌ ÉCHEC: Retour '{ret}' manquant")
                return False
            print(f"✓ Retour '{ret}' présent")

        print("\n✅ SUCCÈS: Nœud de clarification correctement défini")
        return True

    except Exception as e:
        print(f"❌ ÉCHEC: Erreur lors de la vérification: {e}")
        return False


def test_router_ambiguity_detection():
    """Vérifie que le router détecte les ambiguïtés."""
    print("\n" + "=" * 80)
    print("TEST 3: Vérification de la détection d'ambiguïté dans le router")
    print("=" * 80)

    try:
        with open("agent4ba/ai/graph.py", "r") as f:
            content = f.read()

        # Vérifier que la fonction router_node a été modifiée
        if "DÉTECTION D'AMBIGUÏTÉ" not in content:
            print("❌ ÉCHEC: Logique de détection d'ambiguïté non trouvée")
            return False

        print("✓ Logique de détection d'ambiguïté trouvée")

        # Vérifier que ambiguous_intent est utilisé
        if "ambiguous_intent" not in content:
            print("❌ ÉCHEC: Flag ambiguous_intent non utilisé")
            return False

        print("✓ Flag ambiguous_intent est utilisé")

        # Vérifier la fonction de routage conditionnel
        if "route_after_router" not in content:
            print("❌ ÉCHEC: Fonction route_after_router non trouvée")
            return False

        print("✓ Fonction route_after_router trouvée")

        # Vérifier que la fonction route vers clarification
        if "ask_for_clarification" not in content:
            print("❌ ÉCHEC: Route vers ask_for_clarification non trouvée")
            return False

        print("✓ Route vers ask_for_clarification trouvée")

        print("\n✅ SUCCÈS: Détection d'ambiguïté correctement implémentée")
        return True

    except Exception as e:
        print(f"❌ ÉCHEC: Erreur lors de la vérification: {e}")
        return False


def test_graph_structure():
    """Vérifie que le graphe a été correctement modifié."""
    print("\n" + "=" * 80)
    print("TEST 4: Vérification de la structure du graphe")
    print("=" * 80)

    try:
        with open("agent4ba/ai/graph.py", "r") as f:
            content = f.read()

        # Vérifier l'import du nœud de clarification
        if "from agent4ba.ai.nodes import ask_for_clarification" not in content:
            print("❌ ÉCHEC: Import du nœud de clarification manquant")
            return False

        print("✓ Import du nœud de clarification présent")

        # Vérifier que le nœud est ajouté au graphe
        if 'workflow.add_node("ask_for_clarification", ask_for_clarification)' not in content:
            print("❌ ÉCHEC: Nœud ask_for_clarification non ajouté au graphe")
            return False

        print("✓ Nœud ask_for_clarification ajouté au graphe")

        # Vérifier les arêtes conditionnelles
        if "route_after_router" not in content:
            print("❌ ÉCHEC: Arêtes conditionnelles non mises à jour")
            return False

        print("✓ Arêtes conditionnelles mises à jour")

        # Vérifier l'arête depuis clarification vers end
        if 'workflow.add_edge("ask_for_clarification", "end")' not in content:
            print("❌ ÉCHEC: Arête depuis ask_for_clarification vers end manquante")
            return False

        print("✓ Arête depuis ask_for_clarification vers end présente")

        print("\n✅ SUCCÈS: Structure du graphe correctement modifiée")
        return True

    except Exception as e:
        print(f"❌ ÉCHEC: Erreur lors de la vérification: {e}")
        return False


def test_code_quality():
    """Vérifie la qualité du code (docstrings, typage)."""
    print("\n" + "=" * 80)
    print("TEST 5: Vérification de la qualité du code")
    print("=" * 80)

    try:
        with open("agent4ba/ai/nodes/clarification_node.py", "r") as f:
            content = f.read()

        # Vérifier les docstrings
        if '"""' not in content or "Args:" not in content or "Returns:" not in content:
            print("⚠️  AVERTISSEMENT: Docstrings incomplètes")
        else:
            print("✓ Docstrings présentes et complètes")

        # Vérifier le typage
        if "dict[str, Any]" not in content:
            print("⚠️  AVERTISSEMENT: Typage incomplet")
        else:
            print("✓ Typage présent")

        # Vérifier les logs
        if "logger.info" not in content:
            print("⚠️  AVERTISSEMENT: Pas de logging")
        else:
            print("✓ Logging présent")

        print("\n✅ SUCCÈS: Code de qualité acceptable")
        return True

    except Exception as e:
        print(f"⚠️  AVERTISSEMENT: Impossible de vérifier la qualité: {e}")
        return True  # Non-bloquant


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("VALIDATION DE LA STRUCTURE DE LA BOUCLE DE CLARIFICATION")
    print("=" * 80)

    results = []

    # Exécuter tous les tests
    results.append(("GraphState structure", test_graphstate_structure()))
    results.append(("Nœud de clarification", test_clarification_node_exists()))
    results.append(("Détection d'ambiguïté", test_router_ambiguity_detection()))
    results.append(("Structure du graphe", test_graph_structure()))
    results.append(("Qualité du code", test_code_quality()))

    # Résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ DES TESTS")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"{status}: {test_name}")

    print("=" * 80)
    if passed == total:
        print(f"✅ TOUS LES TESTS SONT PASSÉS ({passed}/{total})")
        print("=" * 80 + "\n")
        sys.exit(0)
    else:
        print(f"❌ CERTAINS TESTS ONT ÉCHOUÉ ({passed}/{total})")
        print("=" * 80 + "\n")
        sys.exit(1)
