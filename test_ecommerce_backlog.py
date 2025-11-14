"""
Script de test manuel pour valider le nouveau prompt de génération de backlog.

Test : Génère les features et stories pour un site e-commerce standard
Objectif : Vérifier que le backlog contient des user stories centrées sur l'utilisateur
           et PAS des tâches techniques.
"""

import json
import os
import sys
from agent4ba.ai.backlog_agent import decompose_objective


def test_ecommerce_backlog():
    """Test de génération du backlog pour un site e-commerce."""

    print("=" * 80)
    print("TEST : Génération du backlog pour un site e-commerce")
    print("=" * 80)
    print()

    # Préparer le state
    state = {
        "project_id": "ecommerce-test",
        "intent": {
            "args": {
                "objective": "Génère les features et stories pour un site e-commerce standard"
            }
        },
        "thread_id": "test-ecommerce-123"
    }

    print("Requête : Génère les features et stories pour un site e-commerce standard")
    print()
    print("Appel de la fonction decompose_objective...")
    print()

    try:
        # Appeler la fonction
        result = decompose_objective(state)

        if result.get("status") == "error":
            print("❌ ERREUR lors de la génération :")
            print(result.get("result", "Erreur inconnue"))
            return False

        # Récupérer l'impact plan
        impact_plan = result.get("impact_plan")
        if not impact_plan:
            print("❌ ERREUR : Aucun impact_plan retourné")
            return False

        new_items = impact_plan.get("new_items", [])
        if not new_items:
            print("❌ ERREUR : Aucun work item généré")
            return False

        print(f"✅ {len(new_items)} work items générés")
        print()
        print("=" * 80)
        print("BACKLOG GÉNÉRÉ")
        print("=" * 80)
        print()

        # Afficher les items générés
        for item in new_items:
            item_type = item.get("type", "unknown")
            title = item.get("title", "Sans titre")
            description = item.get("description", "Sans description")

            print(f"[{item_type.upper()}] {title}")
            print(f"Description : {description}")
            print()

        print("=" * 80)
        print("VALIDATION")
        print("=" * 80)
        print()

        # Validation : vérifier qu'il n'y a PAS de tâches techniques
        forbidden_keywords = [
            # Tâches techniques
            "développer", "implémenter", "coder", "programmer", "base de données",
            "api", "backend", "frontend", "serveur", "créer une table",
            # Tâches architecturales
            "architecture", "stack technique", "technologie", "framework",
            "configurer", "installer", "déployer",
            # Tâches de design
            "maquette", "design", "charte graphique", "wireframe", "mockup",
            # Tâches de planification
            "tester", "documenter", "revue de code", "tests unitaires"
        ]

        # Vérifier les user stories
        stories = [item for item in new_items if item.get("type") == "story"]

        validation_passed = True
        issues = []

        for story in stories:
            description = story.get("description", "").lower()
            title = story.get("title", "").lower()

            # Vérifier que c'est au bon format "En tant que..."
            if not description.startswith("en tant que"):
                issues.append(f"❌ Story '{story.get('title')}' ne suit pas le format 'En tant que...'")
                validation_passed = False

            # Vérifier qu'il n'y a pas de mots-clés interdits
            for keyword in forbidden_keywords:
                if keyword in description or keyword in title:
                    issues.append(f"❌ Story '{story.get('title')}' contient un mot-clé technique : '{keyword}'")
                    validation_passed = False

            # Vérifier qu'il n'y a pas "En tant que système/développeur/application"
            bad_personas = ["en tant que système", "en tant que développeur", "en tant qu'application"]
            for persona in bad_personas:
                if persona in description:
                    issues.append(f"❌ Story '{story.get('title')}' utilise un mauvais persona : '{persona}'")
                    validation_passed = False

        # Afficher les résultats de validation
        print("Critères de validation :")
        print()
        print("✅ ATTENDU (user stories centrées utilisateur) :")
        print("  - Recherche de produits")
        print("  - Gestion du panier d'achat")
        print("  - Processus de paiement")
        print("  - Compte utilisateur")
        print()
        print("❌ NON ATTENDU (tâches techniques) :")
        print("  - Choisir la technologie")
        print("  - Définir l'architecture")
        print("  - Faire les maquettes")
        print("  - Créer la base de données")
        print()

        if validation_passed:
            print("=" * 80)
            print("✅ VALIDATION RÉUSSIE")
            print("=" * 80)
            print()
            print("Le backlog ne contient QUE des fonctionnalités utilisateur (QUOI)")
            print("et AUCUNE tâche technique (COMMENT)")
            return True
        else:
            print("=" * 80)
            print("❌ VALIDATION ÉCHOUÉE")
            print("=" * 80)
            print()
            print("Problèmes détectés :")
            for issue in issues:
                print(f"  {issue}")
            return False

    except Exception as e:
        print(f"❌ EXCEPTION : {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Vérifier que les variables d'environnement sont configurées
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ERREUR : Aucune clé API configurée")
        print("Configurez OPENAI_API_KEY ou ANTHROPIC_API_KEY dans le fichier .env")
        sys.exit(1)

    success = test_ecommerce_backlog()
    sys.exit(0 if success else 1)
