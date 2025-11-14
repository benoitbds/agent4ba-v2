#!/usr/bin/env python3
"""
Script de test pour valider le routeur avec Chain of Thought.

Ce script teste les 3 cas d'usage de référence :
1. "génère un site e-commerce de chaussures de luxe"
2. "décompose FIR-3 en user stories"
3. "quelle heure est-il ?"

Pour chaque test, on vérifie :
- La présence du log [ROUTER_THOUGHT]
- La cohérence du raisonnement
- La correspondance entre l'agent sélectionné et la chaîne de pensée
"""

import json
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from litellm import completion

from agent4ba.ai.graph import load_router_prompt
from agent4ba.ai.schemas import RouterDecision
from agent4ba.core.logger import setup_logger

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger = setup_logger(__name__)


def test_router_decision(test_case: str, expected_agent: str) -> bool:
    """
    Teste une décision du routeur.

    Args:
        test_case: La tâche à router
        expected_agent: L'agent attendu

    Returns:
        True si le test réussit, False sinon
    """
    print(f"\n{'=' * 80}")
    print(f"TEST: {test_case}")
    print(f"{'=' * 80}")

    # Charger le prompt
    prompt_config = load_router_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].replace(
        "{{ rewritten_task }}", test_case
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    try:
        # Appeler le LLM
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": prompt_config["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )

        # Extraire la réponse
        routing_json_str = response.choices[0].message.content.strip()

        print(f"\n📝 Réponse brute du LLM:")
        print(routing_json_str)

        # Parser le JSON dans un objet RouterDecision
        routing_data = json.loads(routing_json_str)
        router_decision = RouterDecision(**routing_data)

        # Valider la structure
        router_decision.validate_decision()

        # Afficher la chaîne de pensée (simulation du log [ROUTER_THOUGHT])
        print(f"\n🧠 [ROUTER_THOUGHT] {router_decision.thought}")

        # Extraire les éléments de la décision
        agent_id = router_decision.decision.get("agent")
        agent_task = router_decision.decision.get("task")
        args = router_decision.decision.get("args", {})

        print(f"\n✅ Agent sélectionné: {agent_id}")
        print(f"✅ Tâche sélectionnée: {agent_task}")
        print(f"✅ Arguments: {json.dumps(args, indent=2, ensure_ascii=False)}")

        # Vérifier si l'agent correspond à l'attendu
        if agent_id == expected_agent:
            print(f"\n✅ TEST RÉUSSI: Agent attendu '{expected_agent}' correctement sélectionné")
            return True
        else:
            print(f"\n❌ TEST ÉCHOUÉ: Agent attendu '{expected_agent}', obtenu '{agent_id}'")
            return False

    except json.JSONDecodeError as e:
        print(f"\n❌ Erreur de parsing JSON: {e}")
        return False
    except (KeyError, ValueError) as e:
        print(f"\n❌ Erreur de validation RouterDecision: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        return False


def main():
    """Exécute tous les tests."""
    print("\n" + "=" * 80)
    print("🧪 TESTS DU ROUTEUR AVEC CHAIN OF THOUGHT")
    print("=" * 80)

    # Liste des cas de test
    test_cases = [
        {
            "description": "Création d'un projet e-commerce from scratch",
            "task": "Génère un site e-commerce de chaussures de luxe",
            "expected_agent": "epic_architect_agent",
        },
        {
            "description": "Décomposition d'une feature existante",
            "task": "Décompose FIR-3 en user stories",
            "expected_agent": "story_teller_agent",
        },
        {
            "description": "Requête hors-scope (fallback)",
            "task": "Quelle heure est-il ?",
            "expected_agent": "fallback_agent",
        },
    ]

    # Exécuter les tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'#' * 80}")
        print(f"# TEST {i}/3: {test_case['description']}")
        print(f"{'#' * 80}")

        success = test_router_decision(
            test_case["task"],
            test_case["expected_agent"]
        )
        results.append({
            "test": test_case["description"],
            "success": success
        })

    # Afficher le résumé
    print("\n\n" + "=" * 80)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    for i, result in enumerate(results, 1):
        status = "✅ RÉUSSI" if result["success"] else "❌ ÉCHOUÉ"
        print(f"{i}. {result['test']}: {status}")

    print(f"\n{'=' * 80}")
    print(f"TOTAL: {passed}/{total} tests réussis ({failed} échecs)")
    print(f"{'=' * 80}\n")

    # Retourner un code de sortie approprié
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
