# Refactoring du Graph avec RegistryService

## Résumé des changements

Le fichier `agent4ba/ai/graph.py` a été refactoré pour utiliser la configuration centralisée des agents et des intentions depuis les fichiers YAML, au lieu de la logique codée en dur.

## Modifications apportées

### 1. Chargement de la configuration (lignes 15-31)

```python
from agent4ba.core.registry_service import load_agent_registry

# Charger la configuration des agents et des intentions
_AGENT_REGISTRY = load_agent_registry()

# Créer un dictionnaire de lookup
INTENT_CONFIG_MAP = {
    mapping.intent_id: mapping
    for mapping in _AGENT_REGISTRY.intent_mapping
}
```

- La configuration est chargée **une seule fois** au démarrage du module
- `INTENT_CONFIG_MAP` permet un accès rapide O(1) aux mappings

### 2. GraphState enrichi (ligne 42)

```python
agent_id: str  # ID de l'agent à exécuter (ex: "backlog_agent")
```

- Ajout du champ `agent_id` pour stocker l'agent responsable de l'intention

### 3. router_node refactoré (lignes 155-217)

**Avant** : Utilisait un dictionnaire `intent_to_task` codé en dur

**Après** :
- Utilise `INTENT_CONFIG_MAP` pour récupérer la configuration
- Gère automatiquement les intentions `not_implemented`
- Retourne `agent_id` ET `agent_task` dans l'état

```python
intent_config = INTENT_CONFIG_MAP.get(intent_id)
if intent_config.status == "not_implemented":
    # Route vers end avec message approprié
```

### 4. agent_node refactoré (lignes 257-321)

**Avant** : Dispatchait directement via `agent_task`

**Après** :
- Dispatche d'abord via `agent_id` (backlog_agent ou document_agent)
- Puis route vers la méthode correspondant à `agent_task`
- Architecture plus claire et extensible

```python
if agent_id == "backlog_agent":
    if agent_task == "decompose_objective":
        return backlog_agent.decompose_objective(state)
    # ...
elif agent_id == "document_agent":
    if agent_task == "extract_features":
        return document_agent.extract_requirements(state)
```

## Tests

### Installation des dépendances

```bash
poetry install
```

### Test 1 : Import du module

```bash
poetry run python -c "from agent4ba.ai import graph; print('✓ Import OK')"
```

### Test 2 : Tests automatisés

```bash
poetry run python test_graph_refactoring.py
```

Ce script teste :
- Import du module sans erreur
- Mapping des intentions correctement chargé
- Logique du router_node
- Gestion des intentions not_implemented
- Gestion des faibles scores de confiance

### Test 3 : Test manuel avec workflow complet

Pour tester avec un vrai workflow, utilisez l'API :

```bash
# Démarrer le serveur
poetry run uvicorn agent4ba.api.main:app --reload

# Envoyer une requête
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test-project",
    "user_query": "Décompose l objectif suivant : Créer un système de gestion des utilisateurs"
  }'
```

## Configuration personnalisée

Pour tester la surcharge de configuration :

1. Créer `agent_registry.local.yaml` :

```yaml
# Exemple : Router decompose_objective vers un agent custom
intent_mapping:
  - intent_id: decompose_objective
    agent_id: my_custom_agent  # Modifié !
    agent_task: decompose_objective
    prompt_file: prompts/decompose_objective.yaml
```

2. Redémarrer le serveur

3. Le workflow utilisera automatiquement la nouvelle configuration

## Avantages du refactoring

1. **Maintenabilité** : Configuration centralisée, pas de code dupliqué
2. **Extensibilité** : Ajout d'agents et d'intentions sans modifier graph.py
3. **Flexibilité** : Surcharge locale de configuration via YAML
4. **Validation** : Pydantic garantit la cohérence de la configuration
5. **Testabilité** : Plus facile de tester avec différentes configurations

## Migration progressive

Le refactoring est **compatible** avec le comportement précédent :
- Toutes les intentions existantes fonctionnent exactement comme avant
- Les stubs not_implemented sont préservés
- L'architecture du workflow reste identique

## Prochaines étapes

1. ✅ Refactorer graph.py (FAIT)
2. ⏭️ Refactorer les agents pour utiliser des classes plutôt que des modules
3. ⏭️ Implémenter un système de plugins pour les agents personnalisés
4. ⏭️ Ajouter des tests d'intégration complets
