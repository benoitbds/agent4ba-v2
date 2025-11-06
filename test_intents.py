"""Script de test pour les intentions du workflow."""

import asyncio

import httpx

# Exemples de requêtes pour chaque intention
TEST_QUERIES = [
    {
        "name": "generate_spec",
        "query": "Génère une spécification complète pour la story WI-001",
        "expected_intent": "generate_spec",
    },
    {
        "name": "extract_features",
        "query": "Analyse ce document et extrais-en les fonctionnalités principales",
        "expected_intent": "extract_features_from_docs",
    },
    {
        "name": "review_quality",
        "query": "Fais une revue qualité de mon backlog et dis-moi ce qui manque",
        "expected_intent": "review_backlog_quality",
    },
    {
        "name": "search_requirements",
        "query": "Trouve toutes les stories liées à l'authentification",
        "expected_intent": "search_requirements",
    },
    {
        "name": "decompose_objective",
        "query": "Décompose l'objectif 'système de paiement' en user stories",
        "expected_intent": "decompose_objective",
    },
    {
        "name": "estimate_stories",
        "query": "Estime en story points les items du backlog",
        "expected_intent": "estimate_stories",
    },
    {
        "name": "improve_description",
        "query": "Améliore la description de la story WI-002 pour la rendre plus claire",
        "expected_intent": "improve_item_description",
    },
]


async def test_intent(client: httpx.AsyncClient, test_case: dict) -> None:
    """
    Teste une intention spécifique.

    Args:
        client: Client HTTP async
        test_case: Cas de test
    """
    print(f"\n{'=' * 80}")
    print(f"Testing: {test_case['name']}")
    print(f"Query: {test_case['query']}")
    print(f"Expected intent: {test_case['expected_intent']}")
    print(f"{'=' * 80}")

    try:
        response = await client.post(
            "http://127.0.0.1:8000/chat",
            json={"project_id": "demo", "query": test_case["query"]},
            timeout=30.0,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Result: {result['result']}")
        else:
            print(f"✗ Status: {response.status_code}")
            print(f"✗ Response: {response.text}")

    except Exception as e:
        print(f"✗ Error: {e}")


async def main() -> None:
    """Fonction principale de test."""
    print("Starting intent classification tests...")
    print("Make sure the server is running on http://127.0.0.1:8000")

    async with httpx.AsyncClient() as client:
        # Test health endpoint first
        try:
            health = await client.get("http://127.0.0.1:8000/health")
            if health.status_code == 200:
                print("✓ Server is running\n")
            else:
                print("✗ Server health check failed")
                return
        except Exception as e:
            print(f"✗ Cannot connect to server: {e}")
            return

        # Test each intent
        for test_case in TEST_QUERIES:
            await test_intent(client, test_case)
            await asyncio.sleep(1)  # Pause entre les requêtes


if __name__ == "__main__":
    asyncio.run(main())
