# 🧠 Validation du Routeur avec Chain of Thought (CoT)

## 📋 Contexte

Le routeur d'intention a été transformé en **Orchestrateur Stratégique** avec implémentation de la technique **Chain of Thought (CoT)**. Cette refonte permet au LLM d'expliciter son raisonnement avant chaque décision de routage, rendant le système plus transparent, fiable et auditable.

## 🎯 Changements Implémentés

### 1️⃣ Nouveau Schéma Pydantic `RouterDecision`

**Fichier**: `agent4ba/ai/schemas.py`

```python
class RouterDecision(BaseModel):
    thought: str  # Chaîne de pensée explicitant le raisonnement
    decision: dict  # Décision de routage (agent, task, args)
```

La classe inclut une méthode `validate_decision()` pour garantir la structure correcte de la décision.

### 2️⃣ Prompt Router Refondu

**Fichier**: `prompts/router.yaml`

Le prompt a été complètement réécrit avec les sections suivantes :

- **MISSION**: Définition du rôle d'orchestrateur stratégique
- **AGENTS DISPONIBLES**: Focus sur 3 agents principaux
  - `EpicArchitectAgent`: Création de features de haut niveau (7-15 items)
  - `StoryTellerAgent`: Décomposition de features existantes en user stories
  - `FallbackAgent`: Gestion des requêtes hors-scope

- **PROCESSUS DE DÉCISION OBLIGATOIRE**: 4 étapes structurées
  1. **Analyse Sémantique**: Identifier le besoin fondamental
  2. **Extraction d'Entités**: Détecter les IDs et mots-clés
  3. **Justification**: Comparer et justifier le choix d'agent
  4. **Décision Finale**: Formuler la décision JSON

- **FORMAT DE SORTIE IMPÉRATIF**: Structure JSON avec `thought` + `decision`

### 3️⃣ Modification du `router_node`

**Fichier**: `agent4ba/ai/graph.py`

- Import de `RouterDecision` depuis `agent4ba.ai.schemas`
- Parsing de la réponse LLM en objet `RouterDecision`
- **LOG CRUCIAL**: `logger.info(f"[ROUTER_THOUGHT] {router_decision.thought}")`
- Extraction de `decision` et utilisation comme avant
- Gestion d'erreur robuste avec 3 niveaux :
  - `JSONDecodeError`: Erreur de parsing JSON
  - `KeyError/ValueError`: Erreur de validation de structure
  - `Exception`: Erreur inattendue
  - Tous redirigent vers `fallback_agent` en cas d'échec

## 🧪 Tests de Validation

### Script de Test Automatisé

**Fichier**: `test_router_cot.py`

Le script teste automatiquement les 3 cas d'usage de référence :

```bash
# Exécuter les tests
python test_router_cot.py
```

### Cas de Test

#### 1. **Création d'un projet e-commerce**
- **Requête**: `"Génère un site e-commerce de chaussures de luxe"`
- **Agent attendu**: `epic_architect_agent`
- **Vérifications**:
  - ✅ Présence du log `[ROUTER_THOUGHT]`
  - ✅ Raisonnement mentionne "création from scratch", "liste exhaustive"
  - ✅ Agent sélectionné est `epic_architect_agent`
  - ✅ Tâche est `generate_epics`

#### 2. **Décomposition d'une feature existante**
- **Requête**: `"Décompose FIR-3 en user stories"`
- **Agent attendu**: `story_teller_agent`
- **Vérifications**:
  - ✅ Présence du log `[ROUTER_THOUGHT]`
  - ✅ Raisonnement détecte l'ID "FIR-3"
  - ✅ Agent sélectionné est `story_teller_agent`
  - ✅ Tâche est `decompose_feature_into_stories`
  - ✅ Args contient `{"feature_id": "FIR-3"}`

#### 3. **Requête hors-scope (fallback)**
- **Requête**: `"Quelle heure est-il ?"`
- **Agent attendu**: `fallback_agent`
- **Vérifications**:
  - ✅ Présence du log `[ROUTER_THOUGHT]`
  - ✅ Raisonnement identifie la requête comme hors-scope
  - ✅ Agent sélectionné est `fallback_agent`
  - ✅ Tâche est `handle_unknown_intent`

### Test Manuel avec l'Application

Pour tester le routeur dans l'application réelle :

```bash
# Démarrer le backend
cd backend
python -m uvicorn agent4ba.api.main:app --reload

# Ou utiliser le script de démarrage
./start.sh
```

Puis envoyer des requêtes via l'API ou l'interface web et observer les logs :

```bash
# Observer les logs du backend
tail -f logs/agent4ba.log | grep ROUTER
```

## ✅ Critères de Succès

Le routeur est considéré comme validé si :

1. **Transparence**: Chaque décision affiche un log `[ROUTER_THOUGHT]` avec un raisonnement clair
2. **Précision**: L'agent sélectionné correspond au besoin exprimé dans la requête
3. **Cohérence**: La chaîne de pensée justifie logiquement la décision prise
4. **Résilience**: Les erreurs de parsing sont gérées gracieusement avec redirection vers `fallback_agent`
5. **Auditabilité**: Les logs permettent de comprendre a posteriori pourquoi une décision a été prise

## 📊 Exemples de Logs Attendus

### Exemple 1: EpicArchitectAgent

```
[ROUTER_NODE] Using model: gpt-4o-mini
[ROUTER_THOUGHT] 1. Analyse Sémantique: L'utilisateur souhaite créer un projet complet from scratch. 2. Extraction d'Entités: Aucun ID mentionné, il s'agit d'une création initiale. Mots-clés: 'génère', 'site e-commerce'. 3. Justification: epic_architect_agent est spécialisé dans la génération de listes exhaustives de features de haut niveau pour des projets initiaux. story_teller_agent est écarté car aucun ID de feature n'est fourni. 4. Décision: Utiliser epic_architect_agent avec generate_epics.
[ROUTER_NODE] Selected agent: epic_architect_agent
[ROUTER_NODE] Selected task: generate_epics
[ROUTER_NODE] Extracted args: {'objective': 'site e-commerce de chaussures de luxe'}
```

### Exemple 2: StoryTellerAgent

```
[ROUTER_NODE] Using model: gpt-4o-mini
[ROUTER_THOUGHT] 1. Analyse Sémantique: L'utilisateur demande de décomposer une feature existante en user stories détaillées. 2. Extraction d'Entités: ID 'FIR-3' détecté. Mot-clé: 'décompose'. 3. Justification: story_teller_agent est le spécialiste de la décomposition de features existantes. epic_architect_agent est écarté car il s'agit d'une feature déjà créée, non d'un projet initial. 4. Décision: Utiliser story_teller_agent avec decompose_feature_into_stories.
[ROUTER_NODE] Selected agent: story_teller_agent
[ROUTER_NODE] Selected task: decompose_feature_into_stories
[ROUTER_NODE] Extracted args: {'feature_id': 'FIR-3'}
```

### Exemple 3: FallbackAgent

```
[ROUTER_NODE] Using model: gpt-4o-mini
[ROUTER_THOUGHT] 1. Analyse Sémantique: La requête concerne l'heure, ce qui est complètement hors-scope du système de gestion de backlog. 2. Extraction d'Entités: Aucun ID, aucun mot-clé lié au backlog. 3. Justification: Aucun agent (epic_architect_agent, story_teller_agent) ne correspond à cette requête. Il s'agit d'une question générale sans rapport avec la gestion de projet. 4. Décision: Utiliser fallback_agent pour informer l'utilisateur que la requête est hors-scope.
[ROUTER_NODE] Selected agent: fallback_agent
[ROUTER_NODE] Selected task: handle_unknown_intent
[ROUTER_NODE] Extracted args: {}
```

## 🚀 Prochaines Étapes

1. **Exécuter les tests automatisés** : `python test_router_cot.py`
2. **Tester manuellement avec l'application** : Observer les logs en temps réel
3. **Analyser les logs** : Vérifier la cohérence des chaînes de pensée
4. **Ajuster si nécessaire** : Affiner le prompt si des patterns d'erreur apparaissent

## 📝 Notes Techniques

- Le routeur utilise `temperature=0.0` pour garantir la déterminisme
- Le modèle par défaut est `gpt-4o-mini` (configurable via `DEFAULT_LLM_MODEL`)
- La validation Pydantic garantit que la structure `RouterDecision` est respectée
- En cas d'erreur, le système bascule vers `fallback_agent` plutôt que de crasher

---

**Status**: ✅ Implémentation complète, prête pour validation
**Date**: 2025-11-14
**Branche**: `claude/router-chain-of-thought-012CFewabNPHqp3gk9KURpvv`
