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
- `GET /docs` - Documentation interactive Swagger UI
- `GET /redoc` - Documentation alternative ReDoc

## Structure du projet

```
agent4ba/
├── __init__.py
├── core/               # Modèles de données et logique métier
│   ├── __init__.py
│   ├── models.py      # Modèles Pydantic
│   └── storage.py     # Service de stockage
├── ai/                 # Modules d'intelligence artificielle
│   └── __init__.py
├── api/                # Application FastAPI
│   ├── __init__.py
│   └── main.py        # Application principale
└── data/               # Données persistées
    └── .gitkeep

tests/                  # Tests unitaires et d'intégration
└── .gitkeep
```

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
