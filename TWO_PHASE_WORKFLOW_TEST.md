# Test du Workflow en Deux Phases

## Vue d'ensemble

Ce document décrit le test complet du workflow en deux phases pour la génération de backlog :

1. **Phase 1 (EpicArchitectAgent)** : Génération des features de haut niveau
2. **Phase 2 (StoryTellerAgent)** : Décomposition de chaque feature en user stories

## Architecture

### Agents impliqués

| Agent | Responsabilité | Input | Output |
|-------|----------------|-------|--------|
| **EpicArchitectAgent** | Générer features de haut niveau | Objectif métier (texte) | 7-15 features |
| **StoryTellerAgent** | Décomposer une feature en stories | Feature ID existante | 5-10 user stories |
| **BacklogAgent** | Décomposition complète (legacy) | Objectif métier | Features + Stories |

### Fichiers créés

#### Phase 1 - EpicArchitectAgent
- `agent4ba/ai/epic_architect_agent.py` : Agent de génération de features
- `prompts/generate_epics.yaml` : Prompt système pour features uniquement

#### Phase 2 - StoryTellerAgent
- `agent4ba/ai/story_teller_agent.py` : Agent de décomposition de features
- `prompts/decompose_feature.yaml` : Prompt système pour user stories uniquement

#### Intégration
- `agent4ba/ai/graph.py` : Routing vers les deux nouveaux agents
- `prompts/router.yaml` : Règles de routage mises à jour

## Scénario de test complet

### Étape 1 : Génération des features

**Requête utilisateur :**
```
Génère l'ensemble des features pour un site e-commerce de chaussures de luxe
```

**Routage attendu :**
```json
{
  "agent": "epic_architect_agent",
  "task": "generate_epics",
  "args": {
    "objective": "site e-commerce de chaussures de luxe"
  }
}
```

**Résultat attendu :**
- L'agent génère **6 à 15 features**
- Tous les items sont de type `"feature"`
- Les features couvrent tout le périmètre :
  - Catalogue Produit et Navigation
  - Panier et Processus d'Achat
  - Gestion des Paiements
  - Compte Client
  - Système d'Avis et Notations
  - Gestion des Favoris et Wishlist
  - Suivi des Commandes
  - Interface d'Administration
  - Système de Promotions et Codes Promo
  - Service Client et Support

**ImpactPlan présenté :**
```json
{
  "new_items": [
    {
      "id": "FIR-1",
      "type": "feature",
      "title": "Catalogue Produit et Navigation",
      "description": "...",
      "parent_id": null,
      "attributes": {"priority": "high", "status": "todo", "points": 21}
    },
    {
      "id": "FIR-2",
      "type": "feature",
      "title": "Panier et Processus d'Achat",
      "description": "...",
      "parent_id": null,
      "attributes": {"priority": "high", "status": "todo", "points": 21}
    },
    // ... 8 autres features
  ],
  "modified_items": [],
  "deleted_items": []
}
```

**Action utilisateur :**
✅ **APPROUVER** l'ImpactPlan

**Résultat :**
Le backlog contient maintenant 10 features (FIR-1 à FIR-10) sans user stories.

---

### Étape 2 : Décomposition de la première feature

**Requête utilisateur :**
```
Génère les user stories pour la feature FIR-1
```

**Routage attendu :**
```json
{
  "agent": "story_teller_agent",
  "task": "decompose_feature_into_stories",
  "args": {
    "feature_id": "FIR-1"
  }
}
```

**Processus de l'agent :**
1. Charger le backlog existant
2. Trouver la feature FIR-1 ("Catalogue Produit et Navigation")
3. Vérifier que FIR-1 est bien de type "feature"
4. Extraire le titre et la description de FIR-1
5. Appeler le LLM avec le prompt `decompose_feature.yaml`
6. Générer 5-10 user stories
7. Assigner `parent_id = "FIR-1"` à toutes les stories

**Résultat attendu :**
- L'agent génère **5 à 10 user stories**
- Toutes les stories sont de type `"story"`
- Toutes les stories ont `parent_id = "FIR-1"`
- Les stories couvrent exhaustivement la feature :
  - Afficher la liste des produits
  - Rechercher un produit par mot-clé
  - Filtrer par catégorie
  - Filtrer par taille
  - Filtrer par couleur
  - Filtrer par prix
  - Trier les résultats
  - Voir les détails d'un produit
  - Etc.

**ImpactPlan présenté :**
```json
{
  "new_items": [
    {
      "id": "FIR-11",
      "type": "story",
      "title": "Afficher la liste des produits",
      "description": "En tant que client, je veux voir la liste des chaussures disponibles afin de parcourir le catalogue",
      "parent_id": "FIR-1",
      "attributes": {"priority": "high", "status": "todo", "points": 3}
    },
    {
      "id": "FIR-12",
      "type": "story",
      "title": "Rechercher un produit par mot-clé",
      "description": "En tant que client, je veux rechercher une chaussure par mot-clé afin de trouver rapidement ce que je cherche",
      "parent_id": "FIR-1",
      "attributes": {"priority": "high", "status": "todo", "points": 5}
    },
    // ... 6 autres user stories
  ],
  "modified_items": [],
  "deleted_items": []
}
```

**Action utilisateur :**
✅ **APPROUVER** l'ImpactPlan

**Résultat :**
Le backlog contient maintenant :
- 10 features (FIR-1 à FIR-10)
- 8 user stories enfants de FIR-1 (FIR-11 à FIR-18)

**Affichage attendu dans l'interface :**
```
📦 FIR-1: Catalogue Produit et Navigation
  └─ 📝 FIR-11: Afficher la liste des produits
  └─ 📝 FIR-12: Rechercher un produit par mot-clé
  └─ 📝 FIR-13: Filtrer par catégorie
  └─ 📝 FIR-14: Filtrer par taille
  └─ 📝 FIR-15: Filtrer par couleur
  └─ 📝 FIR-16: Filtrer par prix
  └─ 📝 FIR-17: Trier les résultats
  └─ 📝 FIR-18: Voir les détails d'un produit

📦 FIR-2: Panier et Processus d'Achat
📦 FIR-3: Gestion des Paiements
📦 FIR-4: Compte Client
📦 FIR-5: Système d'Avis et Notations
...
```

---

### Étape 3 : Décomposition de la deuxième feature

**Requête utilisateur :**
```
Décompose la feature FIR-2
```

**Routage attendu :**
```json
{
  "agent": "story_teller_agent",
  "task": "decompose_feature_into_stories",
  "args": {
    "feature_id": "FIR-2"
  }
}
```

**Résultat attendu :**
- Génère 5-10 user stories pour "Panier et Processus d'Achat"
- Stories comme :
  - Ajouter un produit au panier
  - Modifier la quantité
  - Supprimer un produit
  - Vider le panier
  - Voir le récapitulatif
  - Passer à la caisse
  - Etc.

**Répéter pour chaque feature** jusqu'à avoir un backlog complet et structuré.

---

## Critères de validation

### ✅ Phase 1 - EpicArchitectAgent

1. **Routage correct** : Le router dirige vers `epic_architect_agent` quand l'utilisateur demande "l'ensemble des features"

2. **Génération de features uniquement** :
   - ✅ Tous les items sont de type `"feature"`
   - ❌ Aucun item de type `"story"`
   - ❌ Aucune tâche technique

3. **Liste exhaustive** :
   - ✅ Entre 6 et 15 features
   - ✅ Couvre tous les domaines fonctionnels majeurs

4. **Haut niveau d'abstraction** :
   - ✅ Titles comme "Gestion des Paiements", "Catalogue Produit"
   - ❌ Pas de titles détaillés comme "Paiement par carte"

5. **Format correct** :
   - ✅ `parent_id = null` pour toutes les features
   - ✅ Story points élevés (13, 21, 34)

### ✅ Phase 2 - StoryTellerAgent

1. **Routage correct** : Le router dirige vers `story_teller_agent` quand l'utilisateur mentionne un feature_id

2. **Extraction du feature_id** :
   - ✅ Extrait correctement "FIR-1" de "Génère les US pour FIR-1"
   - ✅ Extrait correctement "FEAT-3" de "Décompose la feature FEAT-3"

3. **Validation de la feature** :
   - ✅ Vérifie que la feature existe dans le backlog
   - ✅ Vérifie que l'item est bien de type "feature"
   - ❌ Erreur si l'ID n'existe pas ou n'est pas une feature

4. **Génération de user stories uniquement** :
   - ✅ Tous les items sont de type `"story"`
   - ❌ Aucun item de type `"feature"`

5. **Relation parent-enfant** :
   - ✅ Tous les stories ont `parent_id = feature_id`
   - ✅ Les stories sont visuellement imbriquées sous la feature dans l'UI

6. **Format des user stories** :
   - ✅ Respectent le format : "En tant que [rôle], je veux [action] afin de [bénéfice]"
   - ✅ Story points petits (1, 2, 3, 5, 8)

7. **Liste exhaustive** :
   - ✅ Entre 5 et 10 user stories par feature
   - ✅ Couvre tous les cas d'usage (nominal, erreur, limites)

---

## Cas d'erreur à tester

### Erreur 1 : Feature inexistante

**Requête :** `Génère les user stories pour FIR-999`

**Résultat attendu :**
```json
{
  "status": "error",
  "result": "Feature FIR-999 not found in backlog"
}
```

### Erreur 2 : ID n'est pas une feature

**Requête :** `Décompose la story FIR-11`

(si FIR-11 est une user story, pas une feature)

**Résultat attendu :**
```json
{
  "status": "error",
  "result": "Item FIR-11 is not a feature (type: story)"
}
```

### Erreur 3 : Pas de backlog

**Requête :** `Génère les user stories pour FIR-1`

(sur un projet vide)

**Résultat attendu :**
```json
{
  "status": "error",
  "result": "No backlog found for project TEST"
}
```

---

## Commandes de test

### Test manuel via l'API

```bash
# Démarrer le serveur
python -m agent4ba.api.server

# Terminal 2 : Phase 1 - Générer les features
curl -X POST http://localhost:8000/api/projects/LUXURY/interact \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Génère l'\''ensemble des features pour un site e-commerce de chaussures de luxe"
  }'

# Récupérer le thread_id de la réponse
THREAD_ID="..."

# Approuver l'ImpactPlan
curl -X POST http://localhost:8000/api/projects/LUXURY/approve/$THREAD_ID \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# Terminal 2 : Phase 2 - Décomposer la première feature
curl -X POST http://localhost:8000/api/projects/LUXURY/interact \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Génère les user stories pour la feature FIR-1"
  }'

# Récupérer le nouveau thread_id
THREAD_ID2="..."

# Approuver l'ImpactPlan
curl -X POST http://localhost:8000/api/projects/LUXURY/approve/$THREAD_ID2 \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# Consulter le backlog final
curl http://localhost:8000/api/projects/LUXURY/backlog
```

---

## Vérification finale

### État du backlog après les deux phases

Le backlog doit montrer :

1. **Structure hiérarchique claire** :
   ```
   📦 Feature 1
     └─ 📝 Story 1.1
     └─ 📝 Story 1.2
     └─ 📝 Story 1.3
   📦 Feature 2
     └─ 📝 Story 2.1
     └─ 📝 Story 2.2
   📦 Feature 3 (pas encore décomposée)
   ```

2. **Relation parent-enfant correcte** :
   - Toutes les stories ont `parent_id` pointant vers leur feature
   - Les features n'ont pas de `parent_id` (ou `null`)

3. **Comptage correct** :
   - Nombre total de features : 10
   - Nombre total de stories : 16 (8 pour FIR-1 + 8 pour FIR-2)
   - Total items : 26

4. **Types corrects** :
   - 10 items de type `"feature"`
   - 16 items de type `"story"`
   - 0 items d'autres types

---

## Avantages du workflow en deux phases

### Pour le Product Owner

1. **Contrôle progressif** : Valider d'abord la vision globale (features) avant de détailler
2. **Priorisation facilitée** : Choisir quelles features décomposer en premier
3. **Itératif** : Décomposer feature par feature au fur et à mesure des sprints
4. **Moins intimidant** : Evite l'effet "wall of stories" (100+ stories d'un coup)

### Pour l'équipe

1. **Clarté** : Structure hiérarchique claire (features → stories)
2. **Navigation** : Facile de voir quelles features sont déjà détaillées
3. **Planification** : Planning poker sur les features d'abord, puis sur les stories
4. **Flexibilité** : Peut redétailler une feature si le contexte change

### Pour l'IA

1. **Spécialisation** : Deux agents experts vs un agent généraliste
2. **Qualité** : Prompts optimisés pour chaque niveau d'abstraction
3. **Robustesse** : Validation à chaque étape
4. **Maintenabilité** : Code plus clair et séparé

---

## Prochaines améliorations possibles

1. **Décomposition automatique** : "Décompose toutes les features en user stories"
2. **Re-décomposition** : "Régénère les stories de FIR-1" (écrase les anciennes)
3. **Validation INVEST** : Analyser automatiquement la qualité des stories générées
4. **Estimation** : Générer les story points automatiquement
5. **Critères d'acceptation** : Générer automatiquement pour chaque story
6. **Cas de test** : Générer automatiquement les cas de test pour chaque story

---

## Conclusion

Le workflow en deux phases permet de construire un backlog structuré, hiérarchique et complet :

**Phase 1 (EpicArchitectAgent)** → Vue d'ensemble avec features de haut niveau
**Phase 2 (StoryTellerAgent)** → Détails d'implémentation avec user stories

Cette approche combine le meilleur des deux mondes :
- ✅ Vision globale complète (toutes les features identifiées)
- ✅ Détails progressifs (décomposer feature par feature)
- ✅ Contrôle humain à chaque étape (approbation des ImpactPlans)
- ✅ Flexibilité (peut s'arrêter et reprendre à tout moment)
