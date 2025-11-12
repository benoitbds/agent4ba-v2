# Guide de test - ID séquentiels par projet

## Résumé des modifications

Cette implémentation remplace le système d'ID temporaires (`temp-1`, `temp-2`, etc.) par une nomenclature séquentielle unique par projet (ex: `REC-1`, `MON-2`).

## Fichiers modifiés

1. **agent4ba/core/workitem_utils.py** (NOUVEAU)
   - `generate_project_prefix()` : Génère un préfixe à partir du project_id
   - `get_next_sequential_index()` : Trouve le prochain index séquentiel disponible
   - `assign_sequential_ids()` : Assigne des ID séquentiels aux nouveaux WorkItems

2. **agent4ba/ai/backlog_agent.py**
   - Suppression de `get_next_temp_index()`
   - Utilisation de `assign_sequential_ids()` dans `decompose_objective()`

3. **agent4ba/ai/document_agent.py**
   - Suppression de `get_next_temp_index()`
   - Utilisation de `assign_sequential_ids()` dans `extract_requirements()`

4. **test_sequential_ids.py** (NOUVEAU)
   - Tests unitaires pour valider la logique de génération d'ID

## Format des ID

**Format** : `PREFIX-NUMBER`

**Exemples de préfixes** :
- `recette-mvp` → `REC-1`, `REC-2`, `REC-3`...
- `mon-projet-test` → `MON-1`, `MON-2`, `MON-3`...
- `ab-test` → `AB-1`, `AB-2`...
- `project` → `PRO-1`, `PRO-2`...

Le préfixe est généré en prenant les 3 premières lettres du premier mot du `project_id`, converties en majuscules.

## Tests à effectuer

### Test 1 : Tests unitaires

```bash
# Installer les dépendances (si pas déjà fait)
poetry install

# Exécuter les tests unitaires
poetry run python test_sequential_ids.py
```

**Résultat attendu** : Tous les tests doivent passer ✓

Les tests vérifient :
- La génération de préfixes corrects
- La récupération du prochain index sur projet vide
- La continuation de séquence avec items existants
- L'ignorance des anciens ID temporaires

### Test 2 : Workflow complet sur projet vide

**Scénario** : Première décomposition sur un nouveau projet

1. Lancer le serveur :
   ```bash
   poetry run uvicorn agent4ba.main:app --reload
   ```

2. Créer un nouveau projet "mon-projet-test"

3. Décomposer un objectif (ex: "système d'authentification")

**Résultat attendu** :
- Les WorkItems générés doivent avoir les ID : `MON-1`, `MON-2`, `MON-3`, etc.
- Aucun ID ne doit commencer par `temp-`

### Test 3 : Continuation de séquence

**Scénario** : Seconde décomposition sur le même projet

1. Sur le même projet "mon-projet-test" (qui contient déjà des items `MON-1` à `MON-N`)

2. Décomposer un nouvel objectif (ex: "gestion des profils utilisateur")

**Résultat attendu** :
- Les nouveaux WorkItems doivent continuer la séquence : `MON-{N+1}`, `MON-{N+2}`, etc.
- Pas de collision d'ID
- La séquence doit être continue même si des items ont été supprimés

### Test 4 : Extraction depuis document

**Scénario** : Test avec document_agent

1. Uploader un document dans le projet

2. Extraire des exigences depuis ce document

**Résultat attendu** :
- Les WorkItems extraits doivent suivre la même nomenclature
- La séquence doit continuer celle du backlog existant

### Test 5 : Fonctionnalités existantes

**Scénario** : Vérifier que les autres fonctionnalités marchent toujours

Tester que ces opérations fonctionnent correctement avec les nouveaux ID :
- ✓ Édition d'un WorkItem
- ✓ Amélioration de description
- ✓ Revue qualité INVEST
- ✓ Sélection de contexte (work_item_id)
- ✓ Suppression d'items

## Robustesse du parsing

La logique de parsing des ID existants est robuste et gère :
- Les ID au bon format (`PREFIX-NUMBER`)
- Les anciens ID temporaires (`temp-X`) qui sont ignorés
- Les ID mal formés qui sont ignorés
- Les séquences non continues (ex: `MON-1`, `MON-5`, `MON-10` → prochain = `MON-11`)

## Exemples de logs attendus

### Décomposition sur projet vide

```
[BACKLOG_AGENT] Generated 5 work items
[BACKLOG_AGENT] Assigned sequential IDs starting with project prefix
[BACKLOG_AGENT]   - feature: Authentification (ID: MON-1)
[BACKLOG_AGENT]   - story: Login page (ID: MON-2)
[BACKLOG_AGENT]   - story: Password reset (ID: MON-3)
...
```

### Continuation de séquence

```
[BACKLOG_AGENT] Loaded 3 existing work items
[BACKLOG_AGENT] Generated 2 work items
[BACKLOG_AGENT] Assigned sequential IDs starting with project prefix
[BACKLOG_AGENT]   - feature: Profils (ID: MON-4)
[BACKLOG_AGENT]   - story: Edit profile (ID: MON-5)
```

## Compatibilité

### Migration des projets existants

Les projets existants avec des ID `temp-X` continueront de fonctionner :
- Les anciens items gardent leurs ID `temp-X`
- Les nouveaux items générés utiliseront le nouveau système séquentiel
- Pas de conflit entre `temp-X` et `PREFIX-NUMBER` car les patterns sont différents

### Recommandation

Pour une nomenclature uniforme, il est recommandé de :
1. Créer un nouveau projet pour tester
2. Pour les projets existants en production, une migration manuelle des ID peut être envisagée ultérieurement

## Points de vigilance

1. **Préfixe unique** : Le préfixe dépend du nom du projet. Des noms de projets similaires donneront des préfixes similaires (ex: "recette-mvp" et "recette-prod" donnent tous deux "REC")

2. **Caractères spéciaux** : Les caractères non-alphabétiques dans le `project_id` sont ignorés. Si le project_id ne contient que des chiffres, le préfixe par défaut "PROJ" est utilisé.

3. **Longueur du préfixe** : Le préfixe fait 2 à 3 caractères. Pour les très courts noms (1 lettre), un 'X' est ajouté pour avoir au moins 2 caractères.

## Support

En cas de problème :
1. Vérifier les logs de l'application
2. Exécuter les tests unitaires pour valider la logique
3. Vérifier que le `project_id` est bien défini et valide
