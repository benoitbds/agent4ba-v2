# Implémentation du DiffViewer

## Vue d'ensemble

Cette implémentation ajoute un composant React générique et réutilisable pour afficher les différences entre deux versions d'un WorkItem dans la modale Impact Plan.

## Fichiers créés/modifiés

### 1. `frontend/lib/diff.ts`
Contient la logique de comparaison des WorkItems.

**Fonction principale : `calculateDiff(before: WorkItem, after: WorkItem)`**
- Compare tous les champs d'un WorkItem
- Retourne un objet structuré avec les différences détectées
- Gère les champs simples (title, description, type, etc.)
- Gère les tableaux (acceptance_criteria)
- Gère les attributs (priority, status, points, et attributs personnalisés)

**Types exportés :**
- `SimpleChange<T>` : Représente un changement simple (from → to)
- `ArrayChange<T>` : Représente les changements dans un tableau (added, removed, unchanged)
- `WorkItemDiff` : Structure complète des différences

**Fonction utilitaire : `hasDiff(diff: WorkItemDiff)`**
- Vérifie si un diff contient au moins un changement

### 2. `frontend/components/DiffViewer.tsx`
Composant React générique pour afficher les différences.

**Props :**
- `before: WorkItem` : État précédent
- `after: WorkItem` : État actuel

**Sous-composants :**
- `SimpleChangeDiff` : Affiche les changements de champs texte/nombre avec un affichage côte à côte (before/after)
- `ArrayChangeDiff` : Affiche les changements dans les listes avec des indicateurs visuels :
  - Vert avec "+" pour les ajouts
  - Rouge avec "−" pour les suppressions
  - Gris avec "•" pour les éléments inchangés
- `AttributesDiff` : Affiche les changements d'attributs avec des badges colorés

**Caractéristiques :**
- Support de l'internationalisation avec next-intl
- Affichage uniquement des champs modifiés
- Codes couleur clairs (vert = ajout, rouge = suppression)
- Interface responsive avec Tailwind CSS

### 3. `frontend/components/ImpactPlanModal.tsx`
Intégration du nouveau composant dans la modale existante.

**Modification :**
- Import du composant `DiffViewer`
- Remplacement de l'affichage manuel du diff de description par `<DiffViewer before={before} after={after} />`
- Conservation de l'affichage spécial pour l'analyse INVEST

### 4. `frontend/messages/fr.json` et `frontend/messages/en.json`
Ajout des clés de traduction nécessaires :
- `backlog.description` : "Description"
- `backlog.type` : "Type"
- `backlog.acceptanceCriteria` : "Critères d'acceptation"
- `backlog.attributes` : "Attributs"
- `timeline.noChanges` : "Aucune modification détectée"

### 5. `frontend/tests/lib/diff.test.ts`
Tests unitaires pour la fonction `calculateDiff` :
- Test du changement de titre
- Test de l'ajout de critères d'acceptation
- Test de la modification de critères d'acceptation
- Test des changements d'attributs
- Test de l'absence de changements

## Extensibilité

La solution est conçue pour être facilement extensible :

1. **Nouveaux champs simples** : Ajouter la comparaison dans `calculateDiff` et l'affichage dans `DiffViewer`
2. **Nouveaux champs de type tableau** : Utiliser `compareArrays` et `ArrayChangeDiff`
3. **Nouveaux attributs** : Automatiquement gérés par la fonction `compareAttributes`

## Utilisation

```tsx
import DiffViewer from "@/components/DiffViewer";

<DiffViewer before={workItemBefore} after={workItemAfter} />
```

## Validation

Pour valider l'implémentation :

### Scénario 1 : Ajout de critères d'acceptation
1. Sélectionner un WorkItem
2. Utiliser l'action "Générer les critères d'acceptation"
3. Vérifier dans l'Impact Plan que les nouveaux critères s'affichent en vert avec le symbole "+"

### Scénario 2 : Modification de titre
1. Modifier le titre d'un WorkItem
2. Vérifier dans l'Impact Plan que l'ancien titre s'affiche barré à gauche (fond rouge)
3. Vérifier que le nouveau titre s'affiche en gras à droite (fond vert)

### Scénario 3 : Modification de description
1. Modifier la description d'un WorkItem
2. Vérifier l'affichage côte à côte de l'ancienne et nouvelle description

## Tests

Pour exécuter les tests :

```bash
cd frontend
npm test
```

Les tests vérifient :
- La détection correcte des changements de champs simples
- La détection des ajouts/suppressions dans les tableaux
- La détection des changements d'attributs
- L'absence de détection de changements quand les WorkItems sont identiques

## Notes techniques

- La comparaison des tableaux utilise des `Set` pour une performance optimale
- L'interface supporte l'internationalisation (i18n)
- Le design utilise Tailwind CSS pour un style cohérent avec le reste de l'application
- Les couleurs suivent les conventions UX standards :
  - Rouge pour les suppressions/before
  - Vert pour les ajouts/after
  - Gris pour les éléments inchangés
