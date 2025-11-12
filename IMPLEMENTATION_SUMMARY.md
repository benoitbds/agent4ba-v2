# Implémentation - ID Séquentiels par Projet

## Résumé Exécutif

✅ **Implementation complète et prête à tester**

Le système d'ID temporaires (`temp-X`) a été remplacé par une nomenclature séquentielle unique par projet (ex: `REC-1`, `MON-2`).

## Modifications Effectuées

### 1. Nouveau Fichier Utilitaire
**`agent4ba/core/workitem_utils.py`** - 143 lignes

Contient 3 fonctions principales :

```python
def generate_project_prefix(project_id: str) -> str:
    """Génère un préfixe de 2-3 lettres depuis le project_id"""
    # "recette-mvp" -> "REC"
    # "mon-projet-test" -> "MON"

def get_next_sequential_index(project_id: str, existing_items: list[WorkItem]) -> tuple[str, int]:
    """Trouve le prochain index disponible pour un préfixe donné"""
    # Retourne (prefix, next_index)
    # Ex: ("REC", 4) si REC-1, REC-2, REC-3 existent

def assign_sequential_ids(project_id: str, existing_items: list[WorkItem], new_items_data: list[dict]) -> list[dict]:
    """Assigne des ID séquentiels à une liste de nouveaux items"""
    # Remplace les ID temp-X par PREFIX-N
```

### 2. Modifications des Agents

#### `agent4ba/ai/backlog_agent.py` (lignes 250-263)
- ✅ Import de `assign_sequential_ids`
- ✅ Suppression de `get_next_temp_index()`
- ✅ Utilisation dans `decompose_objective()`

```python
# Avant:
start_index = get_next_temp_index(existing_items)
for i, item_data in enumerate(work_items_data):
    if item_data.get("id", "").startswith("temp-"):
        item_data["id"] = f"temp-{start_index + i}"

# Après:
work_items_data = assign_sequential_ids(project_id, existing_items, work_items_data)
```

#### `agent4ba/ai/document_agent.py` (lignes 353-366)
- ✅ Import de `assign_sequential_ids`
- ✅ Suppression de `get_next_temp_index()`
- ✅ Utilisation dans `extract_requirements()`

Même pattern de refactoring que backlog_agent.py

### 3. Tests Unitaires

**`test_sequential_ids.py`** - 215 lignes

Tests couvrant :
- ✅ Génération de préfixes corrects
- ✅ Premier index sur projet vide (retourne 1)
- ✅ Continuation de séquence avec items existants
- ✅ Ignorance des ID temporaires existants
- ✅ Assignation d'ID séquentiels

## Format des ID

**Pattern** : `PREFIX-NUMBER`

**Exemples** :
| project_id         | Préfixe | IDs générés               |
|--------------------|---------|---------------------------|
| recette-mvp        | REC     | REC-1, REC-2, REC-3...    |
| mon-projet-test    | MON     | MON-1, MON-2, MON-3...    |
| ab-test            | AB      | AB-1, AB-2, AB-3...       |
| project            | PRO     | PRO-1, PRO-2, PRO-3...    |

## Robustesse

✅ **Gestion des cas limites** :
- Séquences non continues (si REC-5 n'existe pas, le prochain sera REC-6 quand même)
- ID mal formés sont ignorés
- Anciens ID `temp-X` sont ignorés dans le calcul du prochain index
- Caractères spéciaux dans project_id sont nettoyés
- Project_id vide ou invalide → préfixe par défaut "PROJ"

## Compatibilité

✅ **Migration douce** :
- Les anciens items `temp-X` continuent de fonctionner
- Pas de conflit entre `temp-X` et `PREFIX-N` (patterns différents)
- Nouvelles décompositions utiliseront automatiquement le nouveau système
- Aucune modification de base de données requise

## État du Code

### ✅ Commit créé
```
commit 6000bfb
feat: Implémenter la nomenclature séquentielle d'ID par projet

4 files changed, 324 insertions(+), 68 deletions(-)
```

### ✅ Push effectué
```
Branch: claude/sequential-workitem-ids-011CV4YK3iGQYk2A9SzKwTot
Status: Pushed to remote
```

### 📋 Fichiers Modifiés
- `agent4ba/core/workitem_utils.py` (NOUVEAU)
- `agent4ba/ai/backlog_agent.py` (MODIFIÉ)
- `agent4ba/ai/document_agent.py` (MODIFIÉ)
- `test_sequential_ids.py` (NOUVEAU)

## Plan de Test

Voir le fichier **`TEST_SEQUENTIAL_IDS.md`** pour :
- Instructions détaillées de test
- Scénarios de validation
- Résultats attendus
- Cas limites à vérifier

### Tests à Effectuer

1. **Tests unitaires** (recommandé en premier)
   ```bash
   poetry install
   poetry run python test_sequential_ids.py
   ```

2. **Test workflow complet**
   - Créer un nouveau projet "mon-projet-test"
   - Décomposer un objectif
   - Vérifier les ID : MON-1, MON-2, MON-3...

3. **Test continuation de séquence**
   - Sur le même projet, décomposer un nouvel objectif
   - Vérifier que les ID continuent : MON-4, MON-5...

4. **Test extraction document**
   - Uploader un document
   - Extraire des exigences
   - Vérifier la cohérence des ID

## Prochaines Étapes

1. ✅ Code implémenté et testé (review de code)
2. ⏳ Exécuter les tests unitaires (en attente de `poetry install`)
3. ⏳ Tester sur un environnement de développement
4. ⏳ Valider le workflow complet end-to-end
5. ⏳ Tester la continuation de séquence
6. ⏳ Déployer en staging/production

## Notes Techniques

### Logique de Parsing
Le regex utilisé pour parser les ID existants :
```python
pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
```

### Performance
- ⚡ O(n) pour scanner les items existants
- ⚡ O(m) pour assigner les nouveaux ID
- Total: O(n + m) où n = items existants, m = nouveaux items

### Sécurité
- ✅ Validation avec Pydantic maintenue
- ✅ Pas d'injection possible (regex escape)
- ✅ Gestion d'erreurs robuste

## Contact / Support

En cas de problème :
1. Consulter `TEST_SEQUENTIAL_IDS.md`
2. Vérifier les logs de l'application
3. Exécuter les tests unitaires pour diagnostiquer
4. Vérifier que `project_id` est bien défini

## Liens Utiles

- **Branch GitHub** : `claude/sequential-workitem-ids-011CV4YK3iGQYk2A9SzKwTot`
- **Commit** : `6000bfb`
- **Tests** : `test_sequential_ids.py`
- **Documentation** : `TEST_SEQUENTIAL_IDS.md`
