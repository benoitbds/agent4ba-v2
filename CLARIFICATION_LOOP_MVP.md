# Boucle de Clarification - MVP

## Vue d'ensemble

Cette implémentation ajoute une capacité de dialogue au workflow LangGraph en permettant au système de détecter des ambiguïtés dans les requêtes utilisateur et de poser des questions de clarification.

## Modifications apportées

### 1. Modèle d'état (`agent4ba/ai/graph.py`)

Ajout de 4 nouveaux champs à `GraphState` :

```python
# Champs pour la boucle de clarification
ambiguous_intent: bool  # Indique si une ambiguïté a été détectée
clarification_needed: bool  # Indique si une clarification est nécessaire
clarification_question: str | None  # Question à poser à l'utilisateur
user_response: str | None  # Réponse de l'utilisateur à la question
```

### 2. Nœud de clarification (`agent4ba/ai/nodes/clarification_node.py`)

Nouveau module créé avec la fonction `ask_for_clarification(state: dict[str, Any]) -> dict[str, Any]`.

**Fonctionnalités :**
- Analyse le contexte pour identifier les éléments ambigus
- Formule une question de clarification appropriée
- Met à jour l'état avec `clarification_needed=True` et la question
- Définit le statut à `"awaiting_clarification"`

**Logique de détection :**
Pour ce MVP, la détection est simulée :
- Si le contexte contient plusieurs work items
- La question liste les items disponibles et demande à l'utilisateur de préciser

### 3. Router modifié (`agent4ba/ai/graph.py`)

**Fonction `router_node` enrichie :**
- Détection d'ambiguïté avant le routage vers l'agent
- Vérification si la requête contient "Tc", "test" ou "cas de test"
- Comptage des work items dans le contexte
- Si ambiguïté détectée (>1 work item), marque `ambiguous_intent=True`

**Nouvelle fonction `route_after_router` :**
```python
def route_after_router(state: GraphState) -> Literal["ask_for_clarification", "agent", "end"]
```

Cette fonction de routage conditionnel :
- Vérifie si `ambiguous_intent` est `True`
- Route vers `"ask_for_clarification"` si ambiguë
- Sinon, continue normalement vers `"agent"` ou `"end"`

### 4. Graphe LangGraph mis à jour

**Modifications du flux :**

```
entry → task_rewriter → router → [route_after_router] → {
    - ask_for_clarification → end  (si ambiguïté détectée)
    - agent → ...               (sinon)
}
```

**Changements techniques :**
- Ajout du nœud `"ask_for_clarification"` au graphe
- Import du nœud depuis `agent4ba.ai.nodes`
- Arêtes conditionnelles mises à jour pour utiliser `route_after_router`
- Arête directe de `"ask_for_clarification"` vers `"end"`

## Tests

### Test de structure (`test_clarification_structure.py`)

Validations effectuées :
1. ✅ Présence des champs de clarification dans `GraphState`
2. ✅ Existence et structure du nœud `ask_for_clarification`
3. ✅ Logique de détection d'ambiguïté dans le router
4. ✅ Structure du graphe correctement modifiée
5. ✅ Qualité du code (docstrings, typage, logging)

### Test fonctionnel (`test_clarification_loop.py`)

Deux scénarios de test :
1. **Requête ambiguë avec plusieurs items** : Vérifie que la clarification est déclenchée
2. **Requête avec un seul item** : Vérifie qu'aucune clarification n'est demandée

## Utilisation

### Scénario d'utilisation type

**Input :**
```python
state = {
    "project_id": "projet_001",
    "user_query": "génère les Tc",
    "context": [
        {"type": "work_item", "id": "US-001", "name": "Authentification"},
        {"type": "work_item", "id": "US-002", "name": "Paiement"},
        {"type": "work_item", "id": "US-003", "name": "Panier"},
    ],
    ...
}
```

**Output attendu :**
```python
{
    "clarification_needed": True,
    "clarification_question": "J'ai détecté plusieurs items... Pour quel item souhaitez-vous continuer ?\n\n1. US-001 - Authentification\n2. US-002 - Paiement\n3. US-003 - Panier\n\nVeuillez préciser le numéro ou l'ID de l'item.",
    "status": "awaiting_clarification",
    ...
}
```

## Architecture

### Flux de données

```
1. Entry Node
   ↓
2. Task Rewriter Node
   ↓
3. Router Node
   - Détecte ambiguïté
   - Marque ambiguous_intent=True si nécessaire
   ↓
4. route_after_router (routage conditionnel)
   ├─ Si ambiguous_intent → ask_for_clarification
   └─ Sinon → agent
   ↓
5. ask_for_clarification
   - Formule la question
   - Met clarification_needed=True
   - Définit clarification_question
   ↓
6. End Node
```

### Points d'extension futurs

Pour étendre cette implémentation :

1. **Reprise du workflow après clarification :**
   - Ajouter un mécanisme pour reprendre l'exécution après la réponse utilisateur
   - Utiliser `interrupt_before` sur le nœud de clarification
   - Traiter `user_response` pour affiner le routage

2. **Détection d'ambiguïté plus sophistiquée :**
   - Utiliser un LLM pour analyser la requête
   - Détecter d'autres types d'ambiguïtés (paramètres manquants, intentions multiples, etc.)

3. **Questions de clarification contextuelles :**
   - Adapter la question selon le type d'agent
   - Proposer des suggestions basées sur l'historique

4. **Gestion de multiples clarifications :**
   - Permettre plusieurs rounds de clarification
   - Suivre l'historique des questions/réponses

## Contraintes et limitations du MVP

- ✅ **Backend uniquement** : Pas de modification de l'API ou du frontend
- ✅ **Typage strict** : Utilisation de Pydantic et type hints
- ✅ **Code modulaire** : Structure claire et testable
- ⚠️ **Détection simulée** : L'ambiguïté est détectée via des règles simples, pas par LLM
- ⚠️ **Pas de reprise** : Le workflow s'arrête après la question de clarification

## Fichiers modifiés

```
agent4ba/ai/graph.py                     (modifié)
agent4ba/ai/nodes/__init__.py           (créé)
agent4ba/ai/nodes/clarification_node.py (créé)
test_clarification_loop.py              (créé)
test_clarification_structure.py         (créé)
CLARIFICATION_LOOP_MVP.md               (créé)
```

## Validation

Pour valider l'implémentation :

```bash
# Test de structure (rapide, pas de dépendances)
python test_clarification_structure.py

# Test fonctionnel (nécessite poetry install)
poetry run python test_clarification_loop.py
```

## Conclusion

✅ **Objectif atteint** : La boucle de clarification est fonctionnelle et intégrée au workflow LangGraph.

✅ **Qualité du code** : Code propre, documenté, typé et testable.

✅ **Tests validés** : Tous les tests de structure passent avec succès.

➡️ **Prochaines étapes** : Implémenter la reprise du workflow après la réponse utilisateur.
