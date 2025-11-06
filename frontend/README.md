# Agent4BA Frontend

Interface utilisateur Next.js pour Agent4BA V2, permettant d'interagir avec le backend d'assistant IA pour la gestion de backlog.

## Fonctionnalités

- 💬 **Chat Interface** - Saisie de requêtes en langage naturel
- ⏱️ **Agent Timeline** - Visualisation en temps réel de l'exécution du workflow
- 📋 **ImpactPlan Validation** - Approbation/rejet des modifications proposées
- 🔄 **SSE Streaming** - Événements streamés en temps réel depuis le backend
- 🎨 **Tailwind CSS** - Interface moderne et responsive
- ⚡ **TypeScript** - Code entièrement typé pour une meilleure maintenabilité

## Prérequis

- Node.js 18+
- npm ou yarn
- Backend Agent4BA V2 en cours d'exécution (voir ../TESTING.md)

## Installation

1. **Installer les dépendances**

```bash
cd frontend
npm install
```

2. **Configurer l'environnement**

Copier le fichier `.env.example` vers `.env.local`:

```bash
cp .env.example .env.local
```

Modifier `.env.local` si nécessaire:

```env
NEXT_PUBLIC_API_URL=http://localhost:8002
```

## Démarrage

### Mode Développement

```bash
npm run dev
```

L'application sera disponible sur [http://localhost:3000](http://localhost:3000)

### Build Production

```bash
npm run build
npm start
```

## Structure du Projet

```
frontend/
├── app/
│   ├── layout.tsx           # Layout principal
│   ├── page.tsx             # Page d'accueil avec orchestration
│   └── globals.css          # Styles globaux Tailwind
├── components/
│   ├── ChatInput.tsx        # Composant de saisie
│   ├── AgentTimeline.tsx    # Timeline des événements
│   └── ImpactPlanModal.tsx  # Modal d'approbation
├── lib/
│   └── api.ts               # Fonctions API (SSE streaming, approbation)
├── types/
│   └── events.ts            # Types TypeScript pour les événements SSE
├── .env.local               # Configuration (non versionné)
└── README.md                # Ce fichier
```

## Utilisation

### 1. Soumettre une Requête

Dans la zone "Nouvelle demande", saisir une requête en langage naturel, par exemple:

```
Décompose l'objectif système de paiement en user stories
```

Cliquer sur "Envoyer".

### 2. Observer la Timeline

La timeline à droite affiche les événements en temps réel:
- 🔗 **Session initialisée** - Thread ID créé
- ▶️ **Nœud démarré** - Un nœud du workflow commence
- ✅ **Nœud terminé** - Un nœud se termine avec sa sortie
- 📋 **ImpactPlan prêt** - Les modifications sont prêtes pour validation

### 3. Valider l'ImpactPlan

Lorsqu'un ImpactPlan est généré, une modale s'affiche avec:
- ✨ **Nouveaux items** - Work items à créer
- ✏️ **Items modifiés** - Work items à modifier
- 🗑️ **Items supprimés** - Work items à supprimer

Cliquer sur **"Approuver"** ou **"Rejeter"** pour valider la décision.

### 4. Vérifier le Résultat

Si approuvé, un nouveau fichier `backlog_vN.json` est créé dans le backend.
Le message de confirmation s'affiche en haut à gauche.

## Événements SSE

Le frontend consomme les événements suivants du backend:

| Type d'événement       | Description                                    |
|------------------------|------------------------------------------------|
| `thread_id`            | Identifiant de session unique                  |
| `node_start`           | Début d'exécution d'un nœud                    |
| `node_end`             | Fin d'exécution d'un nœud (avec output)        |
| `llm_start`            | Début d'appel LLM                              |
| `llm_token`            | Token streamé du LLM                           |
| `llm_end`              | Fin d'appel LLM                                |
| `impact_plan_ready`    | ImpactPlan prêt pour validation                |
| `workflow_complete`    | Workflow terminé                               |
| `error`                | Erreur pendant l'exécution                     |

## Configuration API

Le frontend communique avec le backend via deux endpoints:

### POST /chat (SSE Stream)
```typescript
{
  project_id: string,
  query: string
}
```

Retourne un stream d'événements SSE au format `data: {json}\n\n`

### POST /agent/run/{thread_id}/continue
```typescript
{
  approved: boolean
}
```

Retourne:
```typescript
{
  result: string,
  project_id: string,
  status: string
}
```

## Troubleshooting

### Le stream SSE ne fonctionne pas

1. Vérifier que le backend est bien démarré sur le port 8002
2. Vérifier la configuration `NEXT_PUBLIC_API_URL` dans `.env.local`
3. Vérifier la console du navigateur pour les erreurs CORS

### Erreur CORS

Si vous rencontrez des erreurs CORS, ajouter les headers CORS dans le backend FastAPI:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### La modale ne s'affiche pas

Vérifier que l'événement `impact_plan_ready` est bien reçu dans la timeline.

## Développement

### Linter

```bash
npm run lint
```

### Format du Code

Le projet utilise les conventions Next.js standard et ESLint.

## Technologies

- **Next.js 15** - Framework React
- **React 19** - Bibliothèque UI
- **TypeScript 5** - Typage statique
- **Tailwind CSS 3** - Framework CSS
- **Fetch API** - Streaming SSE

## Licence

Projet interne Agent4BA V2
