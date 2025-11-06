# Agent4BA V2

Backend pour la gestion de backlog assistée par IA.

## Description

Agent4BA V2 est une application backend construite avec FastAPI pour gérer des backlogs de projets de manière intelligente. Ce projet fournit une API RESTful pour créer, gérer et analyser des work items (user stories, tâches, bugs, etc.).

## Prérequis

- Python 3.11+
- Poetry 1.0+

## Installation

Installer les dépendances avec Poetry :

```bash
poetry install
```

## Démarrage du serveur

Lancer le serveur de développement :

```bash
poetry run uvicorn agent4ba.api.main:app --reload
```

Le serveur sera accessible sur `http://127.0.0.1:8000`.

## Endpoints disponibles

- `GET /health` - Point de contrôle de santé de l'API
- `POST /chat` - Interaction avec l'agent via le workflow LangGraph
- `GET /docs` - Documentation interactive Swagger UI
- `GET /redoc` - Documentation alternative ReDoc

### Exemple d'utilisation du endpoint /chat

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"project_id": "demo", "query": "Liste les user stories du backlog"}'
```

Réponse :
```json
{
  "result": "Processed query 'Liste les user stories du backlog' for project demo",
  "project_id": "demo"
}
```

## Structure du projet

```
agent4ba/
├── __init__.py
├── core/               # Modèles de données et logique métier
│   ├── __init__.py
│   ├── models.py      # Modèles Pydantic (WorkItem)
│   └── storage.py     # Service de stockage avec versioning
├── ai/                 # Modules d'intelligence artificielle
│   ├── __init__.py
│   └── graph.py       # Workflow LangGraph avec 5 nœuds
├── api/                # Application FastAPI
│   ├── __init__.py
│   ├── main.py        # Application principale
│   └── schemas.py     # Schémas Pydantic pour l'API
└── data/               # Données persistées (gitignored)
    ├── .gitkeep
    └── projects/
        └── {project_id}/
            └── backlog_vN.json  # Backlogs versionnés

tests/                  # Tests unitaires et d'intégration
└── .gitkeep
```

## Fonctionnalités

### Gestion du backlog versionné

Le système stocke les backlogs de manière versionnée dans `agent4ba/data/projects/{project_id}/backlog_vN.json`.

**Créer un projet de test :**

```bash
# Créer le répertoire du projet
mkdir -p agent4ba/data/projects/demo

# Créer un fichier backlog_v1.json
cat > agent4ba/data/projects/demo/backlog_v1.json << 'EOF'
[
  {
    "id": "WI-001",
    "project_id": "demo",
    "type": "story",
    "title": "Implémenter l'authentification utilisateur",
    "description": "En tant qu'utilisateur, je veux pouvoir me connecter",
    "parent_id": null,
    "attributes": {
      "priority": "high",
      "status": "todo",
      "points": 8
    }
  }
]
EOF
```

**Utiliser le service de stockage :**

```python
from agent4ba.core.storage import ProjectContextService

service = ProjectContextService()

# Charger le backlog
work_items = service.load_context("demo")

# Sauvegarder une nouvelle version
service.save_backlog("demo", work_items)  # Crée backlog_v2.json
```

### Workflow LangGraph

Le workflow est composé de 5 nœuds qui s'exécutent séquentiellement :

1. **entry_node** - Point d'entrée qui reçoit la requête utilisateur
2. **intent_classifier_node** - Classifie l'intention (stub pour le moment)
3. **router_node** - Route vers le bon agent (stub pour le moment)
4. **agent_node** - Exécute la logique métier (stub pour le moment)
5. **end_node** - Point de sortie qui finalise le résultat

Les logs de chaque nœud s'affichent dans la console pour suivre l'exécution.

## Développement

### Qualité du code

Le projet utilise plusieurs outils pour garantir la qualité du code :

**Vérification du formatage avec Ruff :**
```bash
poetry run ruff check agent4ba/
```

**Vérification des types avec MyPy :**
```bash
poetry run mypy agent4ba/
```

**Tests avec Pytest :**
```bash
poetry run pytest
```

## Licence

Propriétaire
