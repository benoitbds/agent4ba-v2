# API Multi-Tours : Guide d'Utilisation

## Vue d'ensemble

L'API Agent4BA supporte désormais des conversations multi-tours, permettant au workflow LangGraph de demander des clarifications à l'utilisateur lorsque la requête est ambiguë.

## Architecture

### Composants

1. **SessionManager** (`agent4ba/api/session_manager.py`)
   - Gère les checkpoints de conversation en mémoire
   - Crée des identifiants uniques de conversation (UUID v4)
   - Sauvegarde et récupère les états de workflow

2. **GraphState étendu** (`agent4ba/ai/graph.py`)
   - `clarification_needed: bool` - Indique si une clarification est nécessaire
   - `clarification_question: str` - Question à poser à l'utilisateur
   - `user_response: str` - Réponse de l'utilisateur à la clarification

3. **Nouveaux endpoints API** (`agent4ba/api/main.py`)
   - `POST /execute` - Lance un workflow de manière synchrone
   - `POST /respond` - Reprend un workflow après une clarification

4. **Schémas Pydantic** (`agent4ba/api/schemas.py`)
   - `ClarificationResponse` - Requête de réponse à une clarification
   - `ClarificationNeededResponse` - Réponse indiquant qu'une clarification est nécessaire

## Flux de travail

### Scénario 1 : Exécution normale (sans clarification)

```
Client → POST /execute
         ↓
    Workflow s'exécute
         ↓
    HTTP 200 avec résultat final
```

### Scénario 2 : Exécution avec clarification

```
Client → POST /execute (requête ambiguë)
         ↓
    Workflow détecte ambiguïté
         ↓
    HTTP 202 avec conversation_id et question
         ↓
Client → POST /respond (avec conversation_id et réponse)
         ↓
    Workflow reprend avec la clarification
         ↓
    HTTP 200 avec résultat final
```

## Exemples d'utilisation

### Exemple 1 : Requête ambiguë nécessitant une clarification

#### Étape 1 : Appel initial avec requête ambiguë

```bash
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "query": "génère les TC"
  }'
```

**Réponse (HTTP 202 Accepted) :**
```json
{
  "status": "clarification_needed",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "question": "Pour quel work item souhaitez-vous générer les cas de test ? Veuillez préciser l'identifiant (ex: FIR-3, US-001)."
}
```

#### Étape 2 : Réponse à la clarification

```bash
curl -X POST "http://localhost:8000/respond" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_response": "pour FIR-3"
  }'
```

**Réponse (HTTP 200 OK) :**
```json
{
  "result": "Successfully created 5 test case work items for work item FIR-3",
  "project_id": "demo",
  "status": "completed",
  "thread_id": null,
  "impact_plan": null
}
```

### Exemple 2 : Requête claire (pas de clarification)

```bash
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "query": "génère les cas de test pour FIR-3"
  }'
```

**Réponse directe (HTTP 200 OK) :**
```json
{
  "result": "Successfully created 5 test case work items for work item FIR-3",
  "project_id": "demo",
  "status": "completed"
}
```

## Cas déclenchant une clarification

Le workflow demande une clarification dans les cas suivants :

1. **Génération de cas de test** sans identifiant de work item
   - Requête : "génère les TC"
   - Question : "Pour quel work item souhaitez-vous générer les cas de test ?"

2. **Génération de critères d'acceptation** sans identifiant
   - Requête : "génère les critères d'acceptation"
   - Question : "Pour quel work item souhaitez-vous générer les critères d'acceptation ?"

3. **Amélioration de description** sans identifiant
   - Requête : "améliore la description"
   - Question : "Pour quel work item souhaitez-vous améliorer la description ?"

## Schémas API

### POST /execute

**Requête :**
```json
{
  "project_id": "string",
  "query": "string",
  "document_content": "string (optionnel)",
  "context": [
    {
      "type": "work_item",
      "id": "FIR-3"
    }
  ]
}
```

**Réponse (HTTP 200) - Succès :**
```json
{
  "result": "string",
  "project_id": "string",
  "status": "completed"
}
```

**Réponse (HTTP 202) - Clarification nécessaire :**
```json
{
  "status": "clarification_needed",
  "conversation_id": "uuid",
  "question": "string"
}
```

### POST /respond

**Requête :**
```json
{
  "conversation_id": "uuid",
  "user_response": "string"
}
```

**Réponse (HTTP 200) :**
```json
{
  "result": "string",
  "project_id": "string",
  "status": "completed",
  "thread_id": null,
  "impact_plan": null
}
```

## Gestion des sessions

### Durée de vie des sessions

- Les sessions sont stockées en mémoire via le `SessionManager`
- Une session est créée au début de chaque appel à `/execute`
- La session est supprimée après :
  - Une exécution réussie (HTTP 200)
  - Une erreur (HTTP 500)
  - Un appel réussi à `/respond` (HTTP 200)

### MVP vs Production

**MVP (implémentation actuelle) :**
- Stockage en mémoire (dictionnaire Python)
- Perte des sessions en cas de redémarrage du serveur
- Pas de limite de temps sur les sessions

**Production (recommandations futures) :**
- Utiliser Redis ou une base de données pour persister les sessions
- Implémenter un TTL (Time To Live) pour les sessions
- Ajouter un endpoint pour nettoyer les sessions expirées
- Implémenter une limite sur le nombre de sessions actives

## Tests manuels

### Prérequis

1. Lancer le serveur FastAPI :
```bash
poetry install
poetry run uvicorn agent4ba.api.main:app --reload --host 0.0.0.0 --port 8000
```

2. S'assurer qu'un projet existe (ex: "demo")

### Scénario de test : Génération de cas de test avec clarification

1. **Créer une requête ambiguë** qui nécessitera une clarification
2. **Vérifier la réponse HTTP 202** avec conversation_id et question
3. **Fournir la clarification** via `/respond`
4. **Vérifier la réponse HTTP 200** avec le résultat final

### Utilisation avec Postman / Swagger UI

L'API FastAPI génère automatiquement une documentation interactive accessible à :
```
http://localhost:8000/docs
```

Vous pouvez tester les endpoints directement depuis cette interface.

## Implémentation technique

### Détection des clarifications (router_node)

Le `router_node` dans `agent4ba/ai/graph.py` détecte automatiquement les cas nécessitant une clarification :

```python
if agent_task in ["generate_test_cases", "generate_acceptance_criteria", "improve_description"]:
    if not args.get("item_id"):
        clarification_needed = True
        clarification_question = "Pour quel work item souhaitez-vous {task} ?"
```

### Reprise après clarification

Lorsqu'une `user_response` est présente, le `router_node` combine la réponse avec la tâche originale :

```python
if user_response:
    rewritten_task = f"{rewritten_task} {user_response}"
```

Cela permet au LLM d'extraire les informations manquantes (comme l'item_id) de la réponse de l'utilisateur.

## Limitations connues

1. **Stockage en mémoire** : Les sessions sont perdues au redémarrage du serveur
2. **Pas de timeout** : Les sessions persistent indéfiniment en mémoire
3. **Un seul tour de clarification** : Le workflow supporte actuellement une seule clarification par conversation
4. **Pas de contexte conversationnel** : Chaque appel à `/execute` crée une nouvelle session indépendante

## Évolutions futures

1. **Multi-tours de clarifications** : Supporter plusieurs échanges de clarification
2. **Contexte conversationnel** : Maintenir l'historique des échanges
3. **Persistence Redis** : Stocker les sessions dans Redis pour la résilience
4. **Timeouts configurables** : Expirer automatiquement les sessions anciennes
5. **Métriques** : Ajouter des métriques sur les taux de clarification et les durées de session
