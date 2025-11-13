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

## Configuration

### Clés API LLM

Le système utilise LiteLLM pour la classification d'intentions. Vous devez configurer une clé API pour utiliser un modèle LLM.

1. Copier le fichier de configuration exemple :

```bash
cp .env.example .env
```

2. Éditer `.env` et ajouter votre clé API :

```bash
# Pour OpenAI (GPT-4o-mini - recommandé)
OPENAI_API_KEY=sk-votre-clé-api-openai

# OU pour Anthropic (Claude 3 Haiku)
ANTHROPIC_API_KEY=sk-ant-votre-clé-api-anthropic

# Choisir le modèle
DEFAULT_LLM_MODEL=gpt-4o-mini  # ou "claude-3-haiku-20240307"
LLM_TEMPERATURE=0.0
```

**Note:** Sans clé API valide, le système fonctionnera mais toutes les requêtes de classification échoueront gracieusement avec un message d'erreur approprié.

### Configuration JWT pour l'authentification

Le système utilise JWT (JSON Web Tokens) pour l'authentification. Configurez les variables suivantes dans votre fichier `.env` :

```bash
# Configuration JWT (obligatoire pour l'authentification)
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**IMPORTANT :** En production, générez une clé secrète sécurisée avec :
```bash
openssl rand -hex 32
```

## Démarrage du serveur

Lancer le serveur de développement :

```bash
poetry run uvicorn agent4ba.api.main:app --reload
```

Le serveur sera accessible sur `http://127.0.0.1:8000`.

### Configuration de la taille maximale d'upload

La taille maximale d'upload est configurée à **50 Mo** directement dans le code backend via un middleware personnalisé (`MaxBodySizeMiddleware` dans `agent4ba/api/app_factory.py`).

Cette configuration s'applique automatiquement au démarrage du serveur, sans nécessiter de paramètres supplémentaires. Les requêtes dépassant 50 Mo seront rejetées avec une erreur HTTP 413 (Content Too Large).

Pour modifier cette limite, éditez la constante `MAX_UPLOAD_SIZE` dans le fichier `agent4ba/api/app_factory.py`.

## Endpoints disponibles

### Authentification

- `POST /auth/register` - Créer un nouveau compte utilisateur
- `POST /auth/login` - Se connecter et obtenir un token JWT

### Routes protégées (nécessitent authentification)

- `GET /projects` - Lister tous les projets (nécessite un token JWT valide)

### Routes publiques

- `GET /health` - Point de contrôle de santé de l'API
- `POST /chat` - Interaction avec l'agent via le workflow LangGraph
- `GET /docs` - Documentation interactive Swagger UI
- `GET /redoc` - Documentation alternative ReDoc

### Exemple d'utilisation de l'authentification

**1. Créer un compte utilisateur :**

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "john_doe", "password": "securePass123"}'
```

Réponse :
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe"
}
```

**2. Se connecter et obtenir un token :**

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john_doe", "password": "securePass123"}'
```

Réponse :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**3. Utiliser le token pour accéder aux routes protégées :**

```bash
curl -X GET http://127.0.0.1:8000/projects \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Réponse :
```json
["demo", "project1", "project2"]
```

### Flux d'authentification

1. **Inscription** : L'utilisateur s'inscrit via `POST /auth/register` avec un username et un mot de passe
2. **Login** : L'utilisateur se connecte via `POST /auth/login` et reçoit un token JWT
3. **Accès protégé** : L'utilisateur utilise le token dans le header `Authorization: Bearer <token>` pour accéder aux routes protégées
4. **Expiration** : Le token expire après 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)

### Sécurité

- Les mots de passe sont hashés avec **bcrypt** avant stockage
- Les tokens JWT sont signés avec **HS256**
- Les routes protégées vérifient automatiquement la validité du token
- Un token invalide ou expiré renvoie une erreur **HTTP 401 Unauthorized**

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

Le workflow est composé de 5 nœuds qui s'exécutent de manière intelligente :

1. **entry_node** - Point d'entrée qui reçoit la requête utilisateur
2. **intent_classifier_node** - Classifie l'intention avec un LLM (GPT-4o-mini ou Claude 3 Haiku)
3. **router_node** - Route vers le bon agent selon l'intention détectée (routage conditionnel)
4. **agent_node** - Exécute la logique métier appropriée (stub pour le moment)
5. **end_node** - Point de sortie qui finalise le résultat

Les logs de chaque nœud s'affichent dans la console pour suivre l'exécution.

### Intentions Supportées

Le classificateur d'intentions reconnaît les requêtes suivantes :

| Intention | Description | Exemple de requête |
|-----------|-------------|-------------------|
| `generate_spec` | Générer une spécification complète | "Génère une spécification pour la story WI-001" |
| `extract_features_from_docs` | Extraire des fonctionnalités depuis des documents | "Analyse ce document et extrais-en les fonctionnalités" |
| `review_backlog_quality` | Revue qualité du backlog | "Fais une revue qualité de mon backlog" |
| `search_requirements` | Chercher des exigences spécifiques | "Trouve toutes les stories liées à l'authentification" |
| `decompose_objective` | Décomposer un objectif en user stories | "Décompose 'système de paiement' en user stories" |
| `estimate_stories` | Estimer les story points | "Estime en story points les items du backlog" |
| `improve_item_description` | Améliorer une description | "Améliore la description de WI-002" |

**Tester les intentions :**

```bash
# Démarrer le serveur
poetry run uvicorn agent4ba.api.main:app --reload

# Dans un autre terminal, tester avec curl
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"project_id": "demo", "query": "Génère une spécification complète pour la story WI-001"}'

# Ou utiliser le script de test
poetry run python test_intents.py
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
# Exécuter tous les tests
poetry run pytest

# Exécuter avec mode verbose
poetry run pytest -v

# Exécuter uniquement les tests d'authentification
poetry run pytest tests/test_auth_*
```

### Tests Unitaires

Le projet dispose d'une suite complète de tests unitaires pour le module d'authentification :

- **Tests d'inscription** (`tests/test_auth_register.py`) - 6 tests
  - Inscription réussie
  - Gestion des doublons
  - Validation des champs (username, password)
  - Vérification du hashage des mots de passe

- **Tests de login** (`tests/test_auth_login.py`) - 6 tests
  - Login réussi avec génération de JWT
  - Gestion des erreurs (username/password invalides)
  - Validation des champs obligatoires
  - Vérification de la sensibilité à la casse
  - Tests de tokens multiples

- **Tests des routes protégées** (`tests/test_projects_auth.py`) - 8 tests
  - Accès sans token (HTTP 401)
  - Accès avec token invalide
  - Accès avec token valide
  - Vérification de l'expiration des tokens

**Statut des tests** : Tous les tests passent (20/20) ✓

Les fixtures pytest sont centralisées dans `tests/conftest.py` pour garantir l'isolation des tests et éviter les effets de bord entre les différentes suites de tests.

## Licence

Propriétaire
