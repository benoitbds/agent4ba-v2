# Test de l'EpicArchitectAgent

## Objectif

Valider que l'EpicArchitectAgent génère correctement une liste exhaustive de features de haut niveau, sans générer de user stories.

## Tests à effectuer

### Test 1 : E-commerce de chaussures de luxe

**Requête :**
```
Génère l'ensemble des features pour un site e-commerce de chaussures de luxe
```

**Résultat attendu :**
- L'agent `epic_architect_agent` est appelé avec la tâche `generate_epics`
- L'ImpactPlan contient entre 6 et 15 items
- Tous les items sont de type `feature`
- Les titres sont des grands thèmes fonctionnels :
  - Catalogue Produit
  - Gestion des Paiements
  - Compte Client
  - Panier et Checkout
  - Système d'Avis
  - Interface d'Administration
  - Suivi des Commandes
  - Etc.
- AUCUN item de type `story` n'est présent

### Test 2 : Application de VTC

**Requête :**
```
Liste exhaustive des features pour une application de VTC
```

**Résultat attendu :**
- L'agent `epic_architect_agent` est appelé
- Génère des features comme :
  - Réservation de Course
  - Suivi du Chauffeur en Temps Réel
  - Gestion des Paiements
  - Profil Utilisateur
  - Système de Notation et Avis
  - Interface Chauffeur
  - Etc.

### Test 3 : Vérification du routage

**Requêtes à tester pour vérifier que le router dirige correctement :**

| Requête | Agent attendu | Task attendue |
|---------|--------------|---------------|
| "Génère l'ensemble des features pour un site e-commerce" | epic_architect_agent | generate_epics |
| "Toutes les features de haut niveau pour un CRM" | epic_architect_agent | generate_epics |
| "Liste exhaustive des features pour un blog" | epic_architect_agent | generate_epics |
| "Décomposer la feature 'Paiement' en user stories" | backlog_agent | decompose_objective |
| "Créer les user stories pour la connexion" | backlog_agent | decompose_objective |

## Commandes de test

### Test manuel via l'API

```bash
# Démarrer le serveur
python -m agent4ba.api.server

# Dans un autre terminal, envoyer la requête
curl -X POST http://localhost:8000/api/projects/TEST/interact \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Génère l'\''ensemble des features pour un site e-commerce de chaussures de luxe"
  }'
```

### Test via les tests unitaires

Créer un test unitaire dans `tests/unit/test_epic_architect_agent.py` :

```python
def test_generate_epics_ecommerce():
    """Test de génération d'epics pour un e-commerce."""
    state = {
        "project_id": "TEST",
        "intent": {
            "args": {
                "objective": "site e-commerce de chaussures de luxe"
            }
        },
        "thread_id": "test-thread-123"
    }

    # Mock du LLM pour retourner des features
    with patch('agent4ba.ai.epic_architect_agent.completion') as mock_completion:
        mock_response = [
            {
                "id": "temp-1",
                "type": "feature",
                "title": "Catalogue Produit",
                "description": "...",
                "parent_id": None,
                "attributes": {"priority": "high", "status": "todo", "points": 21}
            },
            # ... autres features
        ]

        mock_completion.return_value.choices[0].message.content = json.dumps(mock_response)

        result = epic_architect_agent.generate_epics(state)

        assert result["status"] == "awaiting_approval"
        assert len(result["impact_plan"]["new_items"]) >= 6
        for item in result["impact_plan"]["new_items"]:
            assert item["type"] == "feature"
```

## Critères de validation

### ✅ Succès

L'implémentation est considérée comme réussie si :

1. **Routage correct** : Le router dirige vers `epic_architect_agent` quand l'utilisateur demande "l'ensemble des features", "toutes les features", "liste des features"

2. **Génération de features uniquement** : L'agent génère UNIQUEMENT des items de type `feature`, jamais de `story`

3. **Liste exhaustive** : Pour un site e-commerce, l'agent génère entre 6 et 15 features couvrant tous les domaines fonctionnels

4. **Haut niveau d'abstraction** : Les features sont des grands chantiers fonctionnels, pas des détails d'implémentation

5. **Format correct** : L'ImpactPlan est correctement structuré avec `new_items`, `modified_items`, `deleted_items`

### ❌ Échec

L'implémentation doit être corrigée si :

1. L'agent génère des user stories en plus des features
2. L'agent génère des tâches techniques
3. La liste de features est incomplète (moins de 6 items pour un e-commerce)
4. Le routage ne fonctionne pas correctement
5. Les features sont trop détaillées (au niveau user story)

## Notes d'implémentation

### Fichiers créés/modifiés

1. **`prompts/generate_epics.yaml`** : Nouveau prompt système pour l'EpicArchitectAgent
2. **`agent4ba/ai/epic_architect_agent.py`** : Nouvel agent avec la fonction `generate_epics`
3. **`agent4ba/ai/graph.py`** : Intégration du nouvel agent dans le graphe
4. **`prompts/router.yaml`** : Mise à jour du prompt de routage avec l'EpicArchitectAgent

### Différences avec BacklogAgent

| Aspect | EpicArchitectAgent | BacklogAgent |
|--------|-------------------|--------------|
| **Objectif** | Générer UNIQUEMENT des features de haut niveau | Générer features + user stories |
| **Niveau d'abstraction** | Très élevé (grands chantiers) | Mixte (features et détails) |
| **Nombre d'items** | 7-15 features | 1 feature + 3-5 stories |
| **Cas d'usage** | Vue d'ensemble d'un projet | Décomposition détaillée d'une feature |
| **Prompt** | `generate_epics.yaml` | `decompose_objective.yaml` |

## Prochaines étapes

Après validation de l'EpicArchitectAgent, les prochaines étapes seraient :

1. **Story Decomposer Agent** : Créer un agent pour décomposer une feature spécifique en user stories
2. **Workflow en deux étapes** :
   - Étape 1 : EpicArchitectAgent génère les features
   - Étape 2 : Pour chaque feature, Story Decomposer génère les user stories
3. **Interface UI** : Améliorer l'interface pour permettre la décomposition progressive
