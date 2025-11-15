# Validation du système SSE de Timeline

## Résumé de l'implémentation

Le système de Server-Sent Events (SSE) pour la timeline a été implémenté avec succès. Voici ce qui a été créé :

### 1. **Timeline Service** (`agent4ba/api/timeline_service.py`)

- **Modèle `TimelineEvent`** :
  - `event_id` : UUID unique
  - `timestamp` : ISO 8601
  - `type` : Type d'événement (ex: "ROUTER_THOUGHT", "AGENT_ACTION", "WORKFLOW_START")
  - `agent_name` : Nom de l'agent (optionnel)
  - `message` : Description de l'événement
  - `status` : Statut ("IN_PROGRESS", "SUCCESS", "ERROR")
  - `details` : Détails additionnels (optionnel)

- **Classe `TimelineService`** (Singleton) :
  - Gestion de queues `asyncio.Queue` par session
  - Méthode `add_event(session_id, event)` : thread-safe
  - Méthode `stream_events(session_id)` : générateur async pour SSE
  - Méthode `signal_done(session_id)` : signale la fin du stream
  - Méthode `cleanup_session(session_id)` : nettoie les ressources

### 2. **Endpoint SSE** (`agent4ba/api/main.py`)

Nouvel endpoint : `GET /api/v1/timeline/stream/{session_id}`

- Stream les événements au format SSE
- Headers appropriés pour le streaming (Cache-Control, Connection, X-Accel-Buffering)
- Gestion d'erreurs robuste

### 3. **Intégration dans le graphe** (`agent4ba/ai/graph.py`)

Événements émis dans les nœuds clés :

- **`entry_node`** : `WORKFLOW_START` - début du workflow
- **`task_rewriter_node`** : `TASK_REWRITTEN` - tâche reformulée
- **`router_node`** :
  - `ROUTER_DECIDING` - début du routage
  - `ROUTER_THOUGHT` - pensée du routeur
  - `ROUTER_DECISION` - décision de routage
- **`agent_node`** :
  - `AGENT_START` - début de l'exécution de l'agent
  - `AGENT_COMPLETE` - fin de l'exécution
- **`end_node`** : `WORKFLOW_COMPLETE` - fin du workflow + signal de fin du stream

## Instructions de validation

### Prérequis

1. Installer les dépendances :
   ```bash
   poetry install
   ```

2. Configurer l'environnement (créer un fichier `.env` basé sur `.env.example`)

### Test 1 : Vérification des imports

```bash
poetry run python test_timeline_imports.py
```

Ce script teste :
- Imports du service de timeline
- Création d'événements
- Ajout et récupération d'événements

### Test 2 : Lancement du backend

```bash
poetry run uvicorn agent4ba.api.main:app --host 0.0.0.0 --port 8000
```

### Test 3 : Test SSE en temps réel

#### Terminal 1 : Lancer le backend
```bash
poetry run uvicorn agent4ba.api.main:app --host 0.0.0.0 --port 8000
```

#### Terminal 2 : Exécuter un workflow
```bash
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test_project",
    "query": "Créer une nouvelle fonctionnalité de login"
  }'
```

Récupérer le `thread_id` ou `conversation_id` de la réponse.

#### Terminal 3 : S'abonner au stream SSE
```bash
# Remplacer SESSION_ID par le thread_id/conversation_id obtenu
curl -N http://localhost:8000/api/v1/timeline/stream/SESSION_ID
```

### Exemple de sortie attendue

```
data: {"event_id":"123e4567-e89b-12d3-a456-426614174000","timestamp":"2025-11-15T07:30:00.000Z","type":"WORKFLOW_START","agent_name":null,"message":"Processing query for project test_project","status":"IN_PROGRESS","details":{"project_id":"test_project","user_query":"Créer une nouvelle fonctionnalité de login"}}

data: {"event_id":"223e4567-e89b-12d3-a456-426614174001","timestamp":"2025-11-15T07:30:01.000Z","type":"TASK_REWRITTEN","agent_name":null,"message":"Rewritten task: 'Créer une nouvelle fonctionnalité de login avec authentification sécurisée'","status":"SUCCESS","details":{"rewritten_task":"..."}}

data: {"event_id":"323e4567-e89b-12d3-a456-426614174002","timestamp":"2025-11-15T07:30:02.000Z","type":"ROUTER_DECIDING","agent_name":null,"message":"Router analyzing task and deciding which agent to use...","status":"IN_PROGRESS","details":null}

data: {"event_id":"423e4567-e89b-12d3-a456-426614174003","timestamp":"2025-11-15T07:30:03.000Z","type":"ROUTER_THOUGHT","agent_name":null,"message":"Router thought: 'The user wants to create a login feature...'","status":"IN_PROGRESS","details":{"thought":"..."}}

data: {"event_id":"523e4567-e89b-12d3-a456-426614174004","timestamp":"2025-11-15T07:30:04.000Z","type":"ROUTER_DECISION","agent_name":"backlog_agent","message":"Routing to agent: backlog_agent (task: decompose_objective)","status":"SUCCESS","details":{"agent_id":"backlog_agent","agent_task":"decompose_objective","args":{}}}

data: {"event_id":"623e4567-e89b-12d3-a456-426614174005","timestamp":"2025-11-15T07:30:05.000Z","type":"AGENT_START","agent_name":"backlog_agent","message":"Agent backlog_agent starting task: decompose_objective","status":"IN_PROGRESS","details":{"agent_task":"decompose_objective"}}

data: {"event_id":"723e4567-e89b-12d3-a456-426614174006","timestamp":"2025-11-15T07:30:10.000Z","type":"AGENT_COMPLETE","agent_name":"backlog_agent","message":"Agent backlog_agent completed with status: completed","status":"SUCCESS","details":{"agent_task":"decompose_objective","agent_status":"completed"}}

data: {"event_id":"823e4567-e89b-12d3-a456-426614174007","timestamp":"2025-11-15T07:30:11.000Z","type":"WORKFLOW_COMPLETE","agent_name":null,"message":"Workflow completed with status: completed","status":"SUCCESS","details":{"status":"completed","result":"..."}}
```

### Test 4 : Test avec interface web (optionnel)

Créer un fichier HTML de test :

```html
<!DOCTYPE html>
<html>
<head>
    <title>Timeline SSE Test</title>
</head>
<body>
    <h1>Timeline Events</h1>
    <div id="events"></div>

    <script>
        const sessionId = prompt("Enter session_id:");
        const eventSource = new EventSource(`http://localhost:8000/api/v1/timeline/stream/${sessionId}`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const div = document.createElement('div');
            div.style.border = '1px solid #ccc';
            div.style.padding = '10px';
            div.style.margin = '5px';
            div.innerHTML = `
                <strong>${data.type}</strong> [${data.status}]<br/>
                <em>${data.timestamp}</em><br/>
                ${data.message}
            `;
            document.getElementById('events').appendChild(div);
        };

        eventSource.onerror = (error) => {
            console.error('SSE Error:', error);
        };
    </script>
</body>
</html>
```

## Architecture technique

### Flux de données

```
User Request → /execute endpoint
    ↓
LangGraph Workflow (graph.py)
    ↓
Nodes (entry, task_rewriter, router, agent, end)
    ↓
timeline_service.add_event(thread_id, event)
    ↓
asyncio.Queue (par session)
    ↓
Client SSE ← /api/v1/timeline/stream/{session_id}
```

### Thread-Safety

- Le service utilise `asyncio.get_running_loop()` pour obtenir la boucle courante
- `call_soon_threadsafe()` pour ajouter des événements depuis les agents (threads synchrones)
- `asyncio.Queue` pour la communication asynchrone

### Nettoyage des ressources

- `signal_done()` appelé dans `end_node` pour signaler la fin du stream
- `cleanup_session()` peut être appelé après la déconnexion du client (optionnel)

## Statuts de validation

- ✅ Modèle `TimelineEvent` créé avec typage strict
- ✅ Service `TimelineService` implémenté (singleton, thread-safe)
- ✅ Endpoint SSE `/api/v1/timeline/stream/{session_id}` créé
- ✅ Événements intégrés dans les nœuds du graphe
- ⏳ Tests en attente de l'installation des dépendances

## Prochaines étapes (optionnel)

1. **Persistance** : Sauvegarder les événements dans une base de données
2. **Filtrage** : Permettre au client de filtrer par type d'événement
3. **Reconnexion** : Implémenter un mécanisme de reconnexion avec Last-Event-ID
4. **Métriques** : Ajouter des métriques (temps d'exécution, etc.)
5. **Authentification** : Protéger l'endpoint SSE avec un token

## Contact

Pour toute question ou problème, consulter les logs du serveur avec :
```bash
poetry run uvicorn agent4ba.api.main:app --log-level debug
```
