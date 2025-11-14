"""Test du mécanisme de fallback pour les requêtes hors-scope."""

import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from litellm import completion

# Charger les variables d'environnement
load_dotenv()


def load_router_prompt() -> dict:
    """Charge le prompt de routage depuis le fichier YAML."""
    prompt_path = Path(__file__).parent / "prompts" / "router.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_router_fallback(query: str) -> dict:
    """
    Teste le routeur avec une requête donnée.

    Args:
        query: La requête à tester

    Returns:
        Le JSON de routage retourné par le LLM
    """
    # Charger le prompt
    prompt_config = load_router_prompt()

    # Préparer le prompt utilisateur
    user_prompt = prompt_config["user_prompt_template"].replace(
        "{{ rewritten_task }}", query
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    print(f"\n{'='*60}")
    print(f"Testing query: {query}")
    print(f"Model: {model}")
    print(f"{'='*60}\n")

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

        # Extraire la réponse (JSON de routage)
        routing_json_str = response.choices[0].message.content.strip()

        print(f"LLM Response:\n{routing_json_str}\n")

        # Parser le JSON
        routing_data = json.loads(routing_json_str)

        agent_id = routing_data.get("agent", "unknown")
        agent_task = routing_data.get("task", "unknown")
        args = routing_data.get("args", {})

        print(f"Parsed routing:")
        print(f"  Agent: {agent_id}")
        print(f"  Task: {agent_task}")
        print(f"  Args: {args}")

        return routing_data

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_fallback_node():
    """Teste le nœud de fallback directement."""
    from agent4ba.ai.nodes.fallback_node import handle_unknown_intent

    # Simuler un état de graphe
    state = {
        "user_query": "c'est quoi la météo ?",
        "rewritten_task": "Indiquer la météo actuelle",
        "project_id": "test-project",
    }

    print(f"\n{'='*60}")
    print(f"Testing fallback node")
    print(f"{'='*60}\n")

    result = handle_unknown_intent(state)

    print(f"Fallback node result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Result:\n{result.get('result')}")

    return result


if __name__ == "__main__":
    # Test 1: Requête hors-scope (météo)
    print("\n" + "="*60)
    print("TEST 1: Requête hors-scope - météo")
    print("="*60)
    result1 = test_router_fallback("C'est quoi la météo aujourd'hui ?")
    assert result1["agent"] == "fallback_agent", f"Expected fallback_agent, got {result1['agent']}"
    assert result1["task"] == "handle_unknown_intent", f"Expected handle_unknown_intent, got {result1['task']}"
    print("✓ Test 1 passed: Router correctly identifies out-of-scope query\n")

    # Test 2: Autre requête hors-scope (recette)
    print("\n" + "="*60)
    print("TEST 2: Requête hors-scope - recette")
    print("="*60)
    result2 = test_router_fallback("Donne-moi une recette de gâteau au chocolat.")
    assert result2["agent"] == "fallback_agent", f"Expected fallback_agent, got {result2['agent']}"
    assert result2["task"] == "handle_unknown_intent", f"Expected handle_unknown_intent, got {result2['task']}"
    print("✓ Test 2 passed: Router correctly identifies out-of-scope query\n")

    # Test 3: Requête valide (décomposition)
    print("\n" + "="*60)
    print("TEST 3: Requête valide - décomposition")
    print("="*60)
    result3 = test_router_fallback("Créer les features pour un projet de e-commerce.")
    assert result3["agent"] == "backlog_agent", f"Expected backlog_agent, got {result3['agent']}"
    assert result3["task"] == "decompose_objective", f"Expected decompose_objective, got {result3['task']}"
    print("✓ Test 3 passed: Router correctly routes valid query\n")

    # Test 4: Nœud de fallback
    print("\n" + "="*60)
    print("TEST 4: Fallback node")
    print("="*60)
    result4 = test_fallback_node()
    assert result4["status"] == "completed", f"Expected completed, got {result4['status']}"
    assert "Désolé" in result4["result"], "Expected fallback message"
    print("✓ Test 4 passed: Fallback node works correctly\n")

    print("\n" + "="*60)
    print("ALL TESTS PASSED ✓")
    print("="*60)
