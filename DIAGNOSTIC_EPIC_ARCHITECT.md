# 🔍 Diagnostic : "Unknown agent: EpicArchitectAgent"

## ✅ Statut du Code

Le code est **DÉJÀ À JOUR** ! L'`epic_architect_agent` est correctement intégré :

- ✅ Import présent dans `agent4ba/ai/graph.py` (ligne 14)
- ✅ Gestion dans `agent_node()` (lignes 553-561)
- ✅ Prompt router.yaml utilise `"epic_architect_agent"` (snake_case)
- ✅ Fonction `generate_epics()` existe dans `agent4ba/ai/epic_architect_agent.py`

**Commit d'intégration** : `79e329e` - "feat: Add EpicArchitectAgent for high-level feature generation"

---

## 🐛 Causes Possibles de l'Erreur

Si vous obtenez encore l'erreur "Unknown agent: EpicArchitectAgent", voici les causes possibles :

### 1️⃣ **Problème de Casse (PascalCase vs snake_case)**

**Symptôme** : Le LLM retourne `"EpicArchitectAgent"` au lieu de `"epic_architect_agent"`

**Vérification** :
```bash
# Activer les logs DEBUG et vérifier la sortie du routeur
tail -f logs/agent4ba.log | grep ROUTER
```

Cherchez dans les logs :
- `[ROUTER_NODE] JSON to parse:` - Doit contenir `"agent": "epic_architect_agent"`
- Si vous voyez `"agent": "EpicArchitectAgent"`, c'est le problème !

**Solution** :
Le prompt `router.yaml` utilise déjà les bons exemples en snake_case, mais le LLM peut parfois ignorer cela. Si c'est le cas :

```python
# Ajouter une normalisation dans router_node (après ligne 316)
agent_id = router_decision.decision.get("agent", "backlog_agent")

# Normaliser le nom de l'agent en snake_case
agent_id_normalized = agent_id.lower().replace("agent", "_agent")
if not agent_id_normalized.endswith("_agent"):
    agent_id_normalized += "_agent"
```

### 2️⃣ **Serveur Non Redémarré**

**Symptôme** : Le serveur utilise une ancienne version du code en mémoire

**Vérification** :
```bash
# Vérifier le timestamp du processus Python
ps aux | grep uvicorn
```

**Solution** :
```bash
# Arrêter complètement le serveur
pkill -f uvicorn

# Redémarrer
python -m uvicorn agent4ba.api.main:app --reload
```

### 3️⃣ **Cache Python (__pycache__)**

**Symptôme** : Python charge d'anciens fichiers .pyc

**Solution** :
```bash
# Nettoyer tous les caches Python
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# Redémarrer le serveur
python -m uvicorn agent4ba.api.main:app --reload
```

### 4️⃣ **Mauvaise Branche Git**

**Symptôme** : Vous n'êtes pas sur la bonne branche

**Vérification** :
```bash
git branch
git log --oneline -1
```

**Solution** :
```bash
# S'assurer d'être sur la bonne branche
git checkout claude/router-chain-of-thought-012CFewabNPHqp3gk9KURpvv
git pull origin claude/router-chain-of-thought-012CFewabNPHqp3gk9KURpvv
```

---

## 🧪 Tests de Validation

### Test 1 : Vérifier l'Intégration du Code

```bash
# Vérifier que epic_architect_agent est bien dans agent_node
grep -A 8 'elif agent_id == "epic_architect_agent":' agent4ba/ai/graph.py
```

**Résultat attendu** :
```python
elif agent_id == "epic_architect_agent":
    # Router vers la méthode appropriée de l'epic_architect_agent
    if agent_task == "generate_epics":
        return epic_architect_agent.generate_epics(state)
    else:
        return {
            "status": "error",
            "result": f"Unknown task '{agent_task}' for epic_architect_agent",
        }
```

### Test 2 : Vérifier les Imports

```python
# Dans un shell Python
python3 -c "from agent4ba.ai import epic_architect_agent; print('✅ Import OK')"
python3 -c "from agent4ba.ai.epic_architect_agent import generate_epics; print('✅ generate_epics OK')"
```

### Test 3 : Test Unitaire avec Logs DEBUG

```bash
# Activer les logs DEBUG
export LOG_LEVEL=DEBUG

# Relancer le serveur
python -m uvicorn agent4ba.api.main:app --reload

# Dans un autre terminal, envoyer une requête de test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test",
    "query": "génère un site e-commerce de chaussures"
  }'

# Observer les logs
tail -f logs/agent4ba.log | grep -E "(ROUTER|AGENT_NODE)"
```

**Logs attendus** :
```
[ROUTER_NODE] Raw LLM response: ...
[ROUTER_NODE] Cleaned JSON string: {"thought": "...", "decision": {"agent": "epic_architect_agent", ...}}
[ROUTER_NODE] JSON to parse: {"thought": "...", "decision": {"agent": "epic_architect_agent", ...}}
[ROUTER_THOUGHT] 1. Analyse Sémantique: ...
[ROUTER_NODE] Selected agent: epic_architect_agent
[ROUTER_NODE] Selected task: generate_epics
[AGENT_NODE] Routing to specific agent...
[AGENT_NODE] Agent ID: epic_architect_agent
[AGENT_NODE] Agent task: generate_epics
```

---

## 🛠️ Solution Rapide (Si le Problème Persiste)

Si après toutes ces vérifications le problème persiste, c'est probablement que le LLM retourne parfois la mauvaise casse. Voici un patch robuste :

### Option A : Normalisation dans router_node

```python
# Dans agent4ba/ai/graph.py, après la ligne 325
agent_id = router_decision.decision.get("agent", "backlog_agent")

# Normaliser la casse des noms d'agents
agent_id_map = {
    "epicarchitectagent": "epic_architect_agent",
    "storytelleragent": "story_teller_agent",
    "backlogagent": "backlog_agent",
    "testagent": "test_agent",
    "documentagent": "document_agent",
    "fallbackagent": "fallback_agent",
}

# Tenter de normaliser
normalized_key = agent_id.lower().replace("_", "")
if normalized_key in agent_id_map:
    agent_id = agent_id_map[normalized_key]
    logger.info(f"[ROUTER_NODE] Normalized agent name to: {agent_id}")
```

### Option B : Ajuster le Prompt (plus strict)

Modifier `prompts/router.yaml` pour être encore plus explicite :

```yaml
# Dans la section FORMAT DE SORTIE IMPÉRATIF, ajouter :
ATTENTION : Les noms d'agents doivent être EXACTEMENT en snake_case :
- "epic_architect_agent" (PAS "EpicArchitectAgent" ni "epicArchitectAgent")
- "story_teller_agent" (PAS "StoryTellerAgent" ni "storyTellerAgent")
- "fallback_agent" (PAS "FallbackAgent" ni "fallbackAgent")
```

---

## 📊 Checklist de Diagnostic

Cochez chaque point vérifié :

- [ ] Le code `agent4ba/ai/graph.py` contient bien le bloc `elif agent_id == "epic_architect_agent"`
- [ ] L'import `from agent4ba.ai import ... epic_architect_agent ...` est présent
- [ ] Le serveur backend a été redémarré après les derniers changements
- [ ] Les caches Python (__pycache__) ont été nettoyés
- [ ] Vous êtes sur la branche `claude/router-chain-of-thought-012CFewabNPHqp3gk9KURpvv`
- [ ] Les logs DEBUG montrent `"agent": "epic_architect_agent"` (snake_case)
- [ ] Le test unitaire `python test_agent_node_epic.py` passe (si dépendances installées)

---

## ✅ Résultat Attendu

Après correction, en envoyant la requête `"génère un site e-commerce de chaussures de luxe"` :

1. **Logs** :
   ```
   [ROUTER_THOUGHT] 1. Analyse Sémantique: ...
   [ROUTER_NODE] Selected agent: epic_architect_agent
   [AGENT_NODE] Agent ID: epic_architect_agent
   [AGENT_NODE] Agent task: generate_epics
   ```

2. **Workflow** :
   - ✅ Pas d'erreur "Unknown agent"
   - ✅ `epic_architect_agent.generate_epics()` est appelé
   - ✅ ImpactPlan généré avec 7-15 features
   - ✅ Workflow en pause avec status `awaiting_approval`
   - ✅ Interface affiche le modal de validation

3. **ImpactPlan** :
   ```json
   {
     "new_items": [
       {"type": "feature", "title": "Gestion du Catalogue Produits", ...},
       {"type": "feature", "title": "Panier et Commandes", ...},
       ...
     ]
   }
   ```

---

**Date** : 2025-11-14
**Branche** : `claude/router-chain-of-thought-012CFewabNPHqp3gk9KURpvv`
**Status Code** : Déjà intégré ✅
