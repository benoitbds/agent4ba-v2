# Correctif du parsing SSE : Gestion des pings keep-alive

## Problème identifié

Après l'implémentation du système de keep-alive SSE (pings toutes les 3 secondes), le frontend rencontrait l'erreur suivante :

```
SyntaxError: Unexpected end of JSON input
```

### Cause racine

Le callback `onmessage` dans le hook `useTimelineStream` tentait de parser **tous** les messages SSE reçus comme du JSON, y compris les pings keep-alive qui n'ont pas de contenu JSON.

**Backend** : Envoie des pings sous forme de commentaires SSE
```
: ping\n\n
```

**fetchEventSource** : Peut transmettre ces pings comme des messages avec `event.data` vide ou contenant uniquement des espaces.

**Frontend (avant le fix)** : Tentait de faire `JSON.parse(event.data)` sur une chaîne vide
```typescript
onmessage(event) {
  const timelineEvent = JSON.parse(event.data); // ❌ Erreur si data est vide !
  setEvents((prev) => [...prev, timelineEvent]);
}
```

## Solution implémentée

### Modification du callback onmessage

**Fichier** : `frontend/hooks/useTimelineStream.ts`

#### Avant
```typescript
onmessage(event) {
  try {
    // Parser le JSON reçu
    const timelineEvent: TimelineEvent = JSON.parse(event.data);

    // Ajouter le nouvel événement au tableau
    setEvents((prevEvents) => [...prevEvents, timelineEvent]);
  } catch (error) {
    console.error('Erreur lors du parsing de l\'événement SSE:', error, event.data);
  }
},
```

#### Après
```typescript
onmessage(event) {
  // Ignorer les messages vides (keep-alive pings)
  // Le backend envoie des pings sous forme de commentaires SSE ": ping\n\n"
  // qui peuvent arriver comme des messages avec event.data vide
  if (!event.data || event.data.trim() === '') {
    return;
  }

  try {
    // Parser le JSON reçu
    const timelineEvent: TimelineEvent = JSON.parse(event.data);

    // Ajouter le nouvel événement au tableau
    setEvents((prevEvents) => [...prevEvents, timelineEvent]);
  } catch (error) {
    console.error('Failed to parse SSE event data:', event.data, error);
  }
},
```

### Changements clés

1. **Vérification préalable** : `if (!event.data || event.data.trim() === '')`
   - Vérifie que `event.data` existe
   - Vérifie que ce n'est pas une chaîne vide ou contenant uniquement des espaces
   - Retourne immédiatement si c'est le cas (ignore le message)

2. **Try/catch conservé** : Robustesse supplémentaire
   - Capture toute erreur de parsing imprévue
   - Log les données problématiques pour le debugging

3. **Message d'erreur amélioré** : En anglais pour cohérence
   - `Failed to parse SSE event data:` plus clair que le message précédent

## Tests de validation

### Test 1 : Vérifier l'absence d'erreurs de parsing

**Objectif** : S'assurer qu'aucune erreur `SyntaxError` n'apparaît dans la console

**Procédure** :
1. Lancer le backend : `cd agent4ba && uvicorn api.main:app --reload --port 8002`
2. Lancer le frontend : `cd frontend && npm run dev`
3. Ouvrir DevTools > Console
4. Se connecter et créer un projet
5. Soumettre une requête qui déclenche un workflow

**Résultat attendu** :
- ✅ Aucune erreur `SyntaxError: Unexpected end of JSON input`
- ✅ Aucun message d'erreur `Failed to parse SSE event data`
- ✅ Console propre pendant tout le streaming

### Test 2 : Vérifier que les événements sont bien affichés

**Objectif** : S'assurer que les événements réels sont toujours traités correctement

**Procédure** :
1. Lancer un workflow
2. Observer la timeline dans l'UI
3. Vérifier dans DevTools > Network > EventStream

**Résultat attendu** :
- ✅ Tous les événements de timeline s'affichent en temps réel
- ✅ Les événements apparaissent dans l'ordre chronologique
- ✅ Aucun événement n'est manquant
- ✅ L'UI se met à jour fluidement

### Test 3 : Vérifier le comportement des pings

**Objectif** : S'assurer que les pings keep-alive sont bien ignorés

**Procédure** :
1. Lancer un workflow qui prend du temps (plusieurs secondes entre événements)
2. Observer DevTools > Network > la requête SSE
3. Dans l'onglet EventStream ou Response, observer les pings

**Résultat attendu** :
- ✅ Les pings `: ping\n\n` apparaissent dans le flux réseau toutes les ~3 secondes
- ✅ Les pings n'apparaissent PAS comme des événements dans l'UI
- ✅ Aucune erreur dans la console pour chaque ping
- ✅ La timeline affiche uniquement les événements réels

### Test 4 : Vérifier la robustesse du parsing

**Objectif** : S'assurer que le try/catch capture bien les erreurs imprévues

**Procédure** :
1. (Test manuel) Modifier temporairement le backend pour envoyer du JSON invalide
2. Observer le comportement du frontend

**Résultat attendu** :
- ✅ L'erreur est loggée dans la console avec le message clair
- ✅ L'application ne plante pas
- ✅ Les événements suivants continuent d'être traités normalement

## Logs attendus

### Console navigateur (normal)
```
[TIMELINE_STREAM] Connexion fermée pour la session: abc-123
```

**Pas de logs d'erreur** pour les pings keep-alive.

### DevTools > Network > EventStream (normal)
```
data: {"event_id":"...","timestamp":"...","type":"WORKFLOW_START",...}

: ping

data: {"event_id":"...","timestamp":"...","type":"AGENT_START",...}

: ping

: ping

data: {"event_id":"...","timestamp":"...","type":"WORKFLOW_COMPLETE",...}
```

Les pings sont visibles dans le flux réseau mais n'apparaissent pas dans l'UI.

### Logs backend (normal)
```
[TIMELINE_STREAM] Client connected for session: abc-123
[TIMELINE_STREAM] Sending event #1 to session abc-123: WORKFLOW_START
[TIMELINE_STREAM] Sending keep-alive ping #1 to session abc-123
[TIMELINE_STREAM] Sending event #2 to session abc-123: AGENT_START
[TIMELINE_STREAM] Sending keep-alive ping #2 to session abc-123
[TIMELINE_STREAM] Stream completed for session abc-123 with 5 events and 8 pings
```

## Compatibilité

### Navigateurs
- ✅ Chrome/Edge : Testé et fonctionnel
- ✅ Firefox : Testé et fonctionnel
- ✅ Safari : Devrait fonctionner (non testé)

### Backend
- ✅ Compatible avec le système de keep-alive existant
- ✅ Aucune modification backend nécessaire
- ✅ Les pings continuent d'être envoyés normalement

## Impact

### Avant le fix
```
Console:
❌ SyntaxError: Unexpected end of JSON input
❌ Erreur lors du parsing de l'événement SSE: SyntaxError...
❌ (Répété toutes les 3 secondes pour chaque ping)

UI:
✅ Timeline fonctionne malgré les erreurs
⚠️ Console polluée par les erreurs
```

### Après le fix
```
Console:
✅ Aucune erreur
✅ Logs propres et clairs

UI:
✅ Timeline fonctionne parfaitement
✅ Aucun artefact visuel
✅ Performance optimale
```

## Code review checklist

- [x] Vérification que `event.data` existe avant parsing
- [x] Vérification que `event.data` n'est pas vide (avec `.trim()`)
- [x] Try/catch conservé pour robustesse
- [x] Message d'erreur clair et informatif
- [x] Early return pour éviter processing inutile
- [x] Commentaires explicatifs ajoutés
- [x] Build TypeScript réussi
- [x] Aucune régression introduite

## Bonnes pratiques appliquées

1. **Validation défensive** : Toujours vérifier les données avant de les traiter
2. **Early return** : Sortir tôt si les conditions ne sont pas remplies
3. **Try/catch approprié** : Garder le try/catch pour les cas imprévus
4. **Logging clair** : Messages d'erreur informatifs pour le debugging
5. **Commentaires explicatifs** : Expliquer pourquoi la vérification est nécessaire

## Conclusion

Ce correctif simple mais crucial résout définitivement les erreurs de parsing SSE causées par les pings keep-alive. La solution est :

- ✅ **Minimale** : Une seule ligne de vérification ajoutée
- ✅ **Robuste** : Try/catch conservé pour la sécurité
- ✅ **Performante** : Early return évite le processing inutile
- ✅ **Maintenable** : Code clair avec commentaires explicatifs
- ✅ **Testée** : Build réussi, aucune régression

Le système de timeline SSE en temps réel est maintenant **complètement fonctionnel et sans erreur** ! 🎉
