"""Test pour valider la boucle de clarification dans le workflow LangGraph."""

from agent4ba.ai.graph import app, GraphState


def test_clarification_loop_with_ambiguous_request():
    """
    Test la boucle de clarification avec une requête ambiguë.

    Scénario:
    - Requête utilisateur contenant "Tc" (cas de test)
    - Contexte projet avec plusieurs work items
    - Le graphe doit détecter l'ambiguïté et router vers le nœud de clarification
    - L'état final doit contenir clarification_needed=True et une question

    Expected behavior:
    - Le graphe s'exécute jusqu'au nœud ask_for_clarification
    - clarification_needed est True
    - clarification_question est non-nulle
    - status est "awaiting_clarification"
    """
    # Préparer l'état initial avec une requête ambiguë
    initial_state: GraphState = {
        "project_id": "test_project_001",
        "user_query": "génère les Tc",  # Requête ambiguë mentionnant "Tc"
        "document_content": "",
        "context": [
            # Simuler plusieurs work items dans le contexte
            {
                "type": "work_item",
                "id": "US-001",
                "name": "Authentification utilisateur",
            },
            {
                "type": "work_item",
                "id": "US-002",
                "name": "Gestion du panier",
            },
            {
                "type": "work_item",
                "id": "US-003",
                "name": "Paiement sécurisé",
            },
        ],
        "rewritten_task": "",
        "intent": {},
        "intent_args": {},
        "next_node": "",
        "agent_id": "",
        "agent_task": "",
        "impact_plan": {},
        "status": "",
        "approval_decision": None,
        "result": "",
        "agent_events": [],
        "thread_id": "test_thread_clarification",
        # Champs de clarification
        "ambiguous_intent": False,
        "clarification_needed": False,
        "clarification_question": None,
        "user_response": None,
    }

    # Configurer le thread
    config = {"configurable": {"thread_id": "test_thread_clarification"}}

    # Exécuter le graphe
    print("\n" + "=" * 80)
    print("DÉBUT DU TEST - Boucle de clarification")
    print("=" * 80)
    print(f"Requête utilisateur: {initial_state['user_query']}")
    print(f"Nombre de work items dans le contexte: {len(initial_state['context'])}")
    print("=" * 80 + "\n")

    final_state = None
    for state in app.stream(initial_state, config):
        print(f"\nÉtat actuel: {state}")
        # Capturer le dernier état
        if "__end__" in state:
            # L'état final est dans la clé précédente
            continue
        # Le dernier état avant __end__ est notre état final
        final_state = list(state.values())[0]

    # Vérifications
    print("\n" + "=" * 80)
    print("VÉRIFICATIONS")
    print("=" * 80)

    # Vérifier que final_state existe
    assert final_state is not None, "Le graphe devrait produire un état final"

    # Vérifier que clarification_needed est True
    clarification_needed = final_state.get("clarification_needed", False)
    print(f"✓ clarification_needed: {clarification_needed}")
    assert clarification_needed is True, "clarification_needed devrait être True"

    # Vérifier que clarification_question est non-nulle
    clarification_question = final_state.get("clarification_question")
    print(f"✓ clarification_question: {clarification_question[:100] if clarification_question else None}...")
    assert clarification_question is not None, "clarification_question ne devrait pas être None"
    assert len(clarification_question) > 0, "clarification_question ne devrait pas être vide"

    # Vérifier que le status est "awaiting_clarification"
    status = final_state.get("status", "")
    print(f"✓ status: {status}")
    assert status == "awaiting_clarification", f"status devrait être 'awaiting_clarification', got '{status}'"

    # Vérifier que ambiguous_intent a été détecté
    ambiguous_intent = final_state.get("ambiguous_intent", False)
    print(f"✓ ambiguous_intent: {ambiguous_intent}")
    assert ambiguous_intent is True, "ambiguous_intent devrait être True"

    print("\n" + "=" * 80)
    print("✅ TOUS LES TESTS SONT PASSÉS")
    print("=" * 80)
    print(f"\nQuestion de clarification posée:\n{clarification_question}")
    print("=" * 80 + "\n")


def test_no_clarification_when_single_item():
    """
    Test qu'aucune clarification n'est demandée quand il n'y a qu'un seul item.

    Scénario:
    - Requête utilisateur contenant "Tc"
    - Contexte projet avec UN SEUL work item
    - Le graphe ne devrait PAS détecter d'ambiguïté
    - L'état final ne devrait PAS contenir de clarification

    Expected behavior:
    - Le graphe continue normalement vers l'agent
    - clarification_needed est False ou non défini
    """
    initial_state: GraphState = {
        "project_id": "test_project_002",
        "user_query": "génère les Tc",
        "document_content": "",
        "context": [
            # Un seul work item - pas d'ambiguïté
            {
                "type": "work_item",
                "id": "US-001",
                "name": "Authentification utilisateur",
            },
        ],
        "rewritten_task": "",
        "intent": {},
        "intent_args": {},
        "next_node": "",
        "agent_id": "",
        "agent_task": "",
        "impact_plan": {},
        "status": "",
        "approval_decision": None,
        "result": "",
        "agent_events": [],
        "thread_id": "test_thread_no_clarification",
        # Champs de clarification
        "ambiguous_intent": False,
        "clarification_needed": False,
        "clarification_question": None,
        "user_response": None,
    }

    config = {"configurable": {"thread_id": "test_thread_no_clarification"}}

    print("\n" + "=" * 80)
    print("DÉBUT DU TEST - Pas de clarification avec un seul item")
    print("=" * 80)
    print(f"Requête utilisateur: {initial_state['user_query']}")
    print(f"Nombre de work items dans le contexte: {len(initial_state['context'])}")
    print("=" * 80 + "\n")

    final_state = None
    for state in app.stream(initial_state, config):
        print(f"\nÉtat: {list(state.keys())}")
        if "__end__" in state:
            continue
        final_state = list(state.values())[0]

    print("\n" + "=" * 80)
    print("VÉRIFICATIONS")
    print("=" * 80)

    assert final_state is not None, "Le graphe devrait produire un état final"

    # Vérifier que clarification_needed est False (ou non modifié)
    clarification_needed = final_state.get("clarification_needed", False)
    print(f"✓ clarification_needed: {clarification_needed}")
    assert clarification_needed is False, "clarification_needed devrait être False avec un seul item"

    # Vérifier que ambiguous_intent n'a pas été détecté
    ambiguous_intent = final_state.get("ambiguous_intent", False)
    print(f"✓ ambiguous_intent: {ambiguous_intent}")
    assert ambiguous_intent is False, "ambiguous_intent devrait être False avec un seul item"

    print("\n" + "=" * 80)
    print("✅ TEST PASSÉ - Aucune clarification demandée")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("LANCEMENT DES TESTS DE LA BOUCLE DE CLARIFICATION")
    print("=" * 80 + "\n")

    # Test 1: Requête ambiguë avec plusieurs items
    test_clarification_loop_with_ambiguous_request()

    # Test 2: Pas de clarification avec un seul item
    test_no_clarification_when_single_item()

    print("\n" + "=" * 80)
    print("✅ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS")
    print("=" * 80 + "\n")
