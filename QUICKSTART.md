# Agent4BA V2 - Quick Start Guide

Guide de démarrage rapide pour lancer l'ensemble du système Agent4BA V2 (Backend + Frontend).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (localhost:3000)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Next.js Frontend                                         │  │
│  │  - ChatInput: Saisie utilisateur                          │  │
│  │  - AgentTimeline: Affichage temps réel                    │  │
│  │  - ImpactPlanModal: Validation des changements           │  │
│  └────────────────────────┬─────────────────────────────────┘  │
└────────────────────────────┼────────────────────────────────────┘
                             │ SSE Stream (POST /chat)
                             │ Approval (POST /agent/run/{id}/continue)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (localhost:8002)              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LangGraph Workflow                                       │  │
│  │  entry → intent_classifier → router → agent → approval   │  │
│  │                                                           │  │
│  │  Storage: versioned backlog files (backlog_vN.json)      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  OpenAI / Claude │
                    │      LLM API     │
                    └─────────────────┘
```

## Prérequis

- **Python 3.11+** avec Poetry
- **Node.js 18+** avec npm
- **Clé API LLM** (OpenAI ou Anthropic)

## Installation Complète

### 1. Backend Setup

```bash
# Installer les dépendances Python
poetry install

# Configurer la clé API
cp .env.example .env
# Éditer .env et ajouter votre clé:
# OPENAI_API_KEY=sk-...
# ou
# ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Frontend Setup

```bash
# Aller dans le répertoire frontend
cd frontend

# Installer les dépendances Node.js
npm install

# Vérifier la configuration (optionnel)
# Le fichier .env.local existe déjà avec:
# NEXT_PUBLIC_API_URL=http://localhost:8002
```

## Lancement du Système

### Terminal 1: Backend

```bash
# Depuis la racine du projet
poetry run uvicorn agent4ba.api.main:app --reload --port 8002
```

Vous devriez voir:
```
INFO:     Uvicorn running on http://127.0.0.1:8002 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Terminal 2: Frontend

```bash
# Depuis la racine du projet
cd frontend
npm run dev
```

Vous devriez voir:
```
   ▲ Next.js 15.5.6
   - Local:        http://localhost:3000
   - Environments: .env.local

 ✓ Starting...
 ✓ Ready in 2.1s
```

## Test du Système Complet

### 1. Accéder à l'Interface

Ouvrir le navigateur sur: **http://localhost:3000**

### 2. Soumettre une Requête

Dans le champ de saisie, entrer:
```
Décompose l'objectif système de paiement en user stories
```

Cliquer sur **"Envoyer"**

### 3. Observer la Timeline

La timeline à droite affiche les événements en temps réel:

```
🔗 Session initialisée
   Thread: abc123...

▶️ Nœud démarré
   entry_node

✅ Nœud terminé
   entry_node

▶️ Nœud démarré
   intent_classifier_node

✅ Nœud terminé
   intent_classifier_node

▶️ Nœud démarré
   router_node

✅ Nœud terminé
   router_node

▶️ Nœud démarré
   agent_node

✅ Nœud terminé
   agent_node

📋 ImpactPlan prêt pour validation
   5 nouveaux items
```

### 4. Valider l'ImpactPlan

Une modale s'affiche avec:
- ✨ **Nouveaux items** (Feature + User Stories)
- Détails de chaque work item
- Résumé des changements

Cliquer sur **"Approuver"** pour sauvegarder les changements.

### 5. Vérifier le Résultat

#### Dans l'interface:
```
✅ Approuvé: ImpactPlan approved and applied successfully.
   Added 5 new work items. Backlog saved as version 3.
```

#### Dans le filesystem:
```bash
ls -la agent4ba/data/projects/demo/
# Vous devriez voir un nouveau fichier: backlog_v3.json
```

## Flux de Données Complet

```
1. User Input (Frontend)
   └─> POST /chat {"project_id": "demo", "query": "..."}

2. SSE Stream (Backend → Frontend)
   ├─> data: {"type":"thread_id","thread_id":"xyz"}
   ├─> data: {"type":"node_start","node_name":"entry_node"}
   ├─> data: {"type":"node_end","node_name":"entry_node",...}
   ├─> data: {"type":"node_start","node_name":"intent_classifier_node"}
   ├─> data: {"type":"node_end","node_name":"intent_classifier_node",...}
   ├─> data: {"type":"node_start","node_name":"router_node"}
   ├─> data: {"type":"node_end","node_name":"router_node",...}
   ├─> data: {"type":"node_start","node_name":"agent_node"}
   ├─> data: {"type":"node_end","node_name":"agent_node",...}
   └─> data: {"type":"impact_plan_ready","impact_plan":{...},"thread_id":"xyz"}

3. User Approval (Frontend)
   └─> POST /agent/run/xyz/continue {"approved": true}

4. Backend Processing
   ├─> Load existing backlog
   ├─> Apply ImpactPlan changes
   ├─> Save new version (backlog_v3.json)
   └─> Return success response

5. Frontend Display
   └─> Show confirmation message
```

## Exemples de Requêtes

### Décomposition d'Objectif
```
Décompose l'objectif système de paiement en user stories
```

**Résultat attendu:**
- 1 Feature "Système de paiement"
- 3-5 User Stories

### Autres Intentions Supportées

```
# Review de qualité
Analyse la qualité du backlog et propose des améliorations

# Recherche dans le backlog
Trouve tous les items liés à l'authentification

# Amélioration d'un item
Améliore la description de l'item temp-1

# Estimation
Estime la complexité des user stories du backlog
```

## Troubleshooting

### Backend ne démarre pas

**Erreur:** `Module not found`
```bash
# Réinstaller les dépendances
poetry install
```

**Erreur:** `API key not found`
```bash
# Vérifier .env
cat .env
# S'assurer que OPENAI_API_KEY ou ANTHROPIC_API_KEY est défini
```

### Frontend ne se connecte pas au Backend

**Erreur:** `Failed to fetch` dans la console

1. Vérifier que le backend est lancé sur le port 8002:
   ```bash
   curl http://localhost:8002/health
   # Devrait retourner: {"status":"ok"}
   ```

2. Vérifier la configuration dans `frontend/.env.local`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8002
   ```

3. Vérifier les logs du backend pour les erreurs CORS ou autres
   - Le backend est déjà configuré avec CORS pour `http://localhost:3000`
   - Si vous changez le port du frontend, mettez à jour `allow_origins` dans `agent4ba/api/main.py`

### Stream SSE s'arrête prématurément

1. Vérifier les logs du backend pour les erreurs
2. Vérifier la console du navigateur
3. S'assurer que la clé API LLM est valide

### La modale ne s'affiche pas

1. Vérifier que l'événement `impact_plan_ready` apparaît dans la timeline
2. Ouvrir la console du navigateur pour les erreurs React
3. Vérifier que le thread_id est bien reçu

## Structure des Fichiers de Données

```
agent4ba/data/projects/demo/
├── backlog_v1.json    # Version initiale
├── backlog_v2.json    # Après première modification
└── backlog_v3.json    # Version la plus récente
```

Format d'un fichier backlog:
```json
[
  {
    "id": "temp-1",
    "project_id": "demo",
    "type": "feature",
    "title": "Système de paiement",
    "description": "...",
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
    "type": "user_story",
    "title": "En tant qu'utilisateur, je veux...",
    "description": "...",
    "parent_id": "temp-1",
    "attributes": {
      "priority": "high",
      "status": "todo",
      "points": 5
    }
  }
]
```

## Prochaines Étapes

1. **Explorer les autres intentions**: Tester review_backlog_quality, search_requirements, etc.
2. **Personnaliser les prompts**: Modifier les fichiers YAML dans `agent4ba/prompts/`
3. **Ajouter d'autres agents**: Créer de nouveaux agents dans `agent4ba/ai/`
4. **Améliorer l'UI**: Personnaliser les composants dans `frontend/components/`
5. **Configurer la production**: Voir `DEPLOYMENT.md` (à créer)

## Documentation Additionnelle

- **Backend Testing**: Voir `TESTING.md`
- **Frontend Development**: Voir `frontend/README.md`
- **Architecture Details**: Voir les commits git pour l'historique complet

## Support

Pour signaler un bug ou proposer une amélioration:
1. Créer une issue sur GitHub
2. Inclure les logs du backend et frontend
3. Décrire les étapes pour reproduire le problème

## Version

- Backend: v0.1.0
- Frontend: v0.1.0
- Date: 2025-11-06
