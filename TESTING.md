# Guide de Test - Agent4BA V2

## Test du Backlog Agent avec ImpactPlan

### Prérequis

1. Configurer une clé API LLM valide dans `.env`:
   ```bash
   cp .env.example .env
   # Éditer .env et ajouter votre clé OpenAI ou Anthropic
   ```

2. Démarrer le serveur:
   ```bash
   poetry run uvicorn agent4ba.api.main:app --reload
   ```

### Test de décomposition d'objectif

#### Requête 1: Système de paiement

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "query": "Décompose l'\''objectif système de paiement en user stories"
  }'
```

**Résultat attendu avec clé API valide:**

```json
{
  "result": "Generated 5 work items for objective: système de paiement",
  "project_id": "demo",
  "status": "awaiting_approval",
  "impact_plan": {
    "new_items": [
      {
        "id": "temp-1",
        "project_id": "demo",
        "type": "feature",
        "title": "Intégration du système de paiement",
        "description": "Permettre aux utilisateurs d'effectuer des paiements sécurisés en ligne",
        "parent_id": null,
        "attributes": {
          "priority": "high",
          "status": "todo",
          "points": 21
        }
      },
      {
        "id": "temp-2",
        "project_id": "demo",
        "type": "story",
        "title": "Sélection du mode de paiement",
        "description": "En tant qu'utilisateur, je veux pouvoir choisir mon mode de paiement...",
        "parent_id": "temp-1",
        "attributes": {
          "priority": "high",
          "status": "todo",
          "points": 5
        }
      }
      // ... 3-4 autres user stories
    ],
    "modified_items": [],
    "deleted_items": []
  }
}
```

#### Requête 2: Page de connexion

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "query": "Crée une page de connexion"
  }'
```

**Résultat attendu:** ImpactPlan avec 1 Feature et 3-4 User Stories pour l'authentification.

### Logs attendus

Avec une clé API valide, les logs du serveur doivent afficher:

```
[ENTRY_NODE] Processing query for project: demo
[ENTRY_NODE] User query: Décompose l'objectif système de paiement en user stories
[INTENT_CLASSIFIER_NODE] Classifying user intent with LLM...
[INTENT_CLASSIFIER_NODE] Using model: gpt-4o-mini
[INTENT_CLASSIFIER_NODE] LLM response: {"intent_id":"decompose_objective", ...}
[INTENT_CLASSIFIER_NODE] Detected intent: decompose_objective
[INTENT_CLASSIFIER_NODE] Confidence: 0.96
[ROUTER_NODE] Routing based on intent: decompose_objective
[ROUTER_NODE] Selected agent task: decompose_objective
[ROUTER_NODE] Routing to agent node
[AGENT_NODE] Routing to specific agent...
[AGENT_NODE] Agent task: decompose_objective
[BACKLOG_AGENT] Decomposing objective into work items...
[BACKLOG_AGENT] Objective: système de paiement
[BACKLOG_AGENT] Loaded 3 existing work items
[BACKLOG_AGENT] Using model: gpt-4o-mini
[BACKLOG_AGENT] LLM response received: 2500 characters
[BACKLOG_AGENT] Generated 5 work items
[BACKLOG_AGENT]   - feature: Intégration du système de paiement
[BACKLOG_AGENT]   - story: Sélection du mode de paiement
[BACKLOG_AGENT]   - story: Saisie sécurisée des informations de paiement
[BACKLOG_AGENT]   - story: Confirmation de paiement
[BACKLOG_AGENT]   - story: Gestion des erreurs de paiement
[BACKLOG_AGENT] ImpactPlan created successfully
[BACKLOG_AGENT] - 5 new items
[BACKLOG_AGENT] Workflow paused, awaiting human approval
```

**Note:** Le workflow s'interrompt à ce stade et attend la validation humaine. Le nœud `approval` n'est pas exécuté.

### Vérifications

1. **L'ImpactPlan est retourné:** Le champ `impact_plan` contient une liste non vide dans `new_items`
2. **Status correct:** Le champ `status` est `"awaiting_approval"`
3. **Work items valides:** Chaque work item a les champs requis (id, project_id, type, title, description, parent_id, attributes)
4. **Format User Story:** Les descriptions suivent le format "En tant que [rôle], je veux [action] afin de [bénéfice]"
5. **Hiérarchie:** Les user stories ont `parent_id` pointant vers la feature parent

### Test sans clé API

Sans clé API valide, le système échoue gracieusement:

```json
{
  "result": "Intent confidence too low (0.00). Please rephrase your query.",
  "project_id": "demo",
  "status": "",
  "impact_plan": null
}
```

Logs:
```
[INTENT_CLASSIFIER_NODE] Error calling LLM: ...
[ROUTER_NODE] Low confidence (0.0), routing to end
```

### Prochaines étapes

Une fois l'ImpactPlan reçu:
1. Le frontend affiche les work items proposés à l'utilisateur
2. L'utilisateur valide ou rejette les changements
3. Si validé, un appel ultérieur sauvegarde le backlog avec `storage.save_backlog()`
4. Si rejeté, le workflow est abandonné

## Tests d'autres intentions

### Review backlog quality

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "query": "Fais une revue qualité de mon backlog"
  }'
```

**Résultat attendu:** Message indiquant que cet agent n'est pas encore implémenté (stub).

### Search requirements

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "query": "Trouve toutes les stories liées à l'\''authentification"
  }'
```

**Résultat attendu:** Message stub pour agent search (pas encore implémenté).
