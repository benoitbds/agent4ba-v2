# Matrice de Priorisation - Agent4BA Phase 2

**Date:** 2025-11-14
**Contexte:** Extension des capacités fonctionnelles post-MVP
**Architecture actuelle:** BacklogAgent avec 3 tâches (`decompose_objective`, `improve_description`, `review_quality`)

---

## Matrice de Priorisation des Cas d'Usage

| Cas d'Usage | Valeur Métier (1-5) | Complexité Technique (1-5) | Stratégie d'Implémentation | Recommandation |
|------------|---------------------|---------------------------|---------------------------|----------------|
| **1. Génération de critères d'acceptation** | ⭐⭐⭐⭐⭐ (5) | ⭐⭐ (2) | Ajout méthode `generate_acceptance_criteria` dans BacklogAgent avec prompt YAML structuré (Given/When/Then ou liste bullet). | **Priorité 1** |
| **2. Création de cas de test (Gherkin)** | ⭐⭐⭐⭐ (4) | ⭐⭐ (2) | Ajout méthode `generate_test_cases` dans BacklogAgent avec prompt Gherkin (Feature/Scenario/Given-When-Then). | **Priorité 1** |
| **3. Analyse des dépendances entre US** | ⭐⭐⭐⭐ (4) | ⭐⭐⭐⭐ (4) | Méthode `analyze_dependencies` avec chargement backlog complet + LLM pour détecter relations logiques/techniques/temporelles (graphe de dépendances). | **Priorité 2** |
| **4. Gouvernance du backlog** | ⭐⭐⭐ (3) | ⭐⭐⭐ (3) | Méthode `audit_backlog` avec embeddings (FAISS) pour doublons sémantiques + analyse LLM pour clarté/vagueness + suggestions de nettoyage. | **Priorité 2** |
| **5. Analyse des défauts potentiels** | ⭐⭐⭐ (3) | ⭐⭐⭐ (3) | Méthode `analyze_edge_cases` avec prompt de reasoning pour anticiper edge cases, erreurs, conditions limites (analyse par Story). | **Backlog** |
| **6. Validation normes INVEST** | ~~⭐⭐⭐⭐ (4)~~ | ~~0~~ | **✅ DÉJÀ IMPLÉMENTÉ** dans `review_quality()` (lignes 630-942 de backlog_agent.py) - Analyse complète INVEST avec scores détaillés. | **N/A - Existant** |

---

## Analyse Détaillée

### ✅ Fonctionnalité Existante

**Cas #6 - Validation INVEST** est déjà opérationnelle :
- Méthode `review_quality()` analyse toutes les User Stories
- Évalue 6 critères INVEST avec scores et justifications
- Stocke résultats dans `WorkItem.attributes["invest_analysis"]`
- Suit le pattern standard BacklogAgent (événements, ImpactPlan, approval)

---

### 🎯 Priorité 1 - Développement Immédiat

#### **Cas #1 - Génération de critères d'acceptation**
**Pourquoi maintenant ?**
- **Valeur métier maximale** : Rend les User Stories directement actionnables pour les développeurs
- **Complexité minimale** : Réutilise le pattern existant (1 prompt YAML + 1 méthode BacklogAgent)
- **Renforce le backlog** : Enrichit les US existantes plutôt que de créer de nouveaux items

**Détails techniques :**
```python
# Nouveau fichier: prompts/generate_acceptance_criteria.yaml
# Nouvelle méthode: backlog_agent.generate_acceptance_criteria(state)
# Input: work_item_id depuis context ou intent_args
# Output: ImpactPlan avec modified_items (ajout AC dans attributes)
# Format AC: Liste de critères Given/When/Then ou format bullet
```

#### **Cas #2 - Création de cas de test Gherkin**
**Pourquoi maintenant ?**
- **Complément naturel des AC** : Même workflow (Story → AC → Tests)
- **Valeur QA élevée** : Accélère la phase de test et améliore la couverture
- **Réutilisation de code** : Même pattern que #1 avec format Gherkin

**Détails techniques :**
```python
# Nouveau fichier: prompts/generate_test_cases.yaml
# Nouvelle méthode: backlog_agent.generate_test_cases(state)
# Input: work_item_id (peut inclure AC si déjà générés)
# Output: ImpactPlan avec modified_items (ajout test_cases dans attributes)
# Format: Feature/Scenario/Given-When-Then standard Gherkin
```

---

### 📋 Priorité 2 - Développement Post-Sprint

#### **Cas #3 - Analyse des dépendances**
**Pourquoi après P1 ?**
- **Complexité élevée** : Nécessite lecture complète backlog + analyse de graphe
- **Valeur planification** : Utile mais moins urgent que AC/Tests
- **Dépend du volume** : Plus pertinent quand le backlog grandit

**Détails techniques :**
```python
# Charge TOUS les work items (features + stories)
# LLM analyse relations : bloquant, prérequis, similaire, conflictuel
# Construit graphe de dépendances (NetworkX ou simple dict)
# Output: ImpactPlan avec modified_items enrichis de metadata dependencies
```

#### **Cas #4 - Gouvernance du backlog**
**Pourquoi après P1 ?**
- **Complexité moyenne** : Embeddings + analyse sémantique + LLM
- **Valeur maintenance** : Devient critique quand backlog > 50 items
- **Infrastructure** : Peut réutiliser FAISS existant du DocumentAgent

**Détails techniques :**
```python
# Embeddings FAISS pour détecter doublons sémantiques (seuil cosine > 0.85)
# LLM analyse clarté : descriptions vagues, titres ambigus
# Génère rapport d'audit avec suggestions (merge, clarifier, supprimer)
# Output: Rapport JSON + optionnellement ImpactPlan de nettoyage
```

---

### 🗂️ Backlog - Développement Futur

#### **Cas #5 - Analyse des défauts potentiels**
**Pourquoi en backlog ?**
- **Valeur proactive** : Utile mais moins pressant
- **Overlap avec INVEST** : Le critère "Testable" couvre partiellement les edge cases
- **Nécessite expertise** : Requiert un LLM performant en reasoning (GPT-4 vs 4o-mini)

**Détails techniques :**
```python
# Analyse par Story : données manquantes, conditions limites, concurrence, sécurité
# Prompt de reasoning : "Quels edge cases pourraient faire échouer cette Story ?"
# Output: Liste de risques avec sévérité (Critical/High/Medium/Low)
```

---

## 🚀 Recommandation pour le Prochain Sprint

### Duo Tactique Recommandé : **Cas #1 + Cas #2**

#### **Justification Stratégique**

1. **ROI Immédiat Maximum**
   - Transforme les User Stories en assets actionnables complets
   - Accélère le workflow Dev (AC) + QA (Tests)
   - Valeur métier combinée : **9/10**

2. **Complexité Minimale & Livraison Rapide**
   - Même pattern d'implémentation (1 prompt + 1 méthode BacklogAgent)
   - Complexité technique combinée : **4/10**
   - **Estimation : 2-3 jours pour les deux fonctionnalités**

3. **Réutilisabilité du Code**
   - Structure identique aux méthodes existantes (`improve_description`, `review_quality`)
   - Réutilisation des événements, ImpactPlan, approval flow
   - Code du #1 sert de template pour le #2

4. **Alignement avec Objectif "Renforcer le Backlog Existant"**
   - Enrichit les US déjà créées (vs créer nouveaux types de work items)
   - Complète la chaîne de valeur : Objectif → Features/Stories → **AC → Tests**
   - Prépare le terrain pour l'analyse de dépendances (P2) et la gouvernance (P2)

5. **Synergie Fonctionnelle**
   - Les tests Gherkin peuvent s'appuyer sur les AC générés
   - Permet un workflow intégré : Story → AC → Tests (en 3 appels API)
   - Documentation automatique complète (Story + AC + Scénarios de test)

---

## Prochaines Étapes Techniques

### Sprint N+1 : Implémentation #1 et #2

**Phase 1 - Génération de critères d'acceptation (Jour 1-2)**
1. Créer `prompts/generate_acceptance_criteria.yaml`
2. Implémenter `backlog_agent.generate_acceptance_criteria(state)`
3. Ajouter entrée dans `intention_registry.yaml`
4. Tests unitaires + validation manuelle

**Phase 2 - Création de cas de test (Jour 2-3)**
1. Créer `prompts/generate_test_cases.yaml`
2. Implémenter `backlog_agent.generate_test_cases(state)`
3. Ajouter entrée dans `intention_registry.yaml`
4. Tests unitaires + validation manuelle

**Phase 3 - Intégration Frontend (Jour 3)**
1. Boutons UI "Générer AC" et "Générer Tests" sur modal Work Item
2. Affichage des AC et tests dans l'interface
3. Tests end-to-end

---

## Métriques de Succès

**Sprint N+1 :**
- ✅ Génération d'AC fonctionnelle sur backlog existant
- ✅ Génération de tests Gherkin fonctionnelle
- ✅ Temps de développement ≤ 3 jours
- ✅ Taux d'approbation humaine des AC/tests ≥ 80%

**Sprint N+2 (Priorité 2) :**
- ✅ Analyse de dépendances avec graphe visualisable
- ✅ Gouvernance du backlog avec détection de doublons

---

**Conclusion :** Le duo **Génération AC + Tests Gherkin** offre le meilleur ratio valeur/complexité pour étendre immédiatement les capacités d'Agent4BA tout en consolidant l'usage du backlog créé lors du MVP.
