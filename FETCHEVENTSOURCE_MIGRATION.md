# Migration vers @microsoft/fetch-event-source

## Contexte
L'implémentation native d'EventSource présentait des limitations critiques :
- **Pas de support des headers personnalisés** : Impossible d'envoyer `Authorization: Bearer ...`
- **Erreurs 401 Unauthorized** : Le token devait être passé dans l'URL (insécurité)
- **Retry non contrôlable** : EventSource retry automatiquement sans possibilité de l'empêcher
- **Gestion d'erreur limitée** : Impossible de distinguer les erreurs fatales des erreurs temporaires

## Solution : @microsoft/fetch-event-source
La bibliothèque `@microsoft/fetch-event-source` offre une implémentation SSE robuste basée sur `fetch()` avec support complet des headers et du contrôle du cycle de vie.

## Changements apportés

### 1. Installation de la dépendance
```bash
npm install @microsoft/fetch-event-source
```

**Fichiers modifiés** :
- `frontend/package.json`
- `frontend/package-lock.json`

### 2. Refactorisation du hook useTimelineStream

**Fichier** : `frontend/hooks/useTimelineStream.ts`

#### Avant (EventSource natif)
```typescript
const eventSource = new EventSource(urlWithAuth);

eventSource.onmessage = (event) => {
  // ...
};

eventSource.onerror = (error) => {
  eventSource.close();
};

return () => {
  eventSource.close();
};
```

#### Après (fetchEventSource)
```typescript
const ctrl = new AbortController();
const token = localStorage.getItem('auth_token');

fetchEventSource(eventSourceUrl, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
  signal: ctrl.signal,

  onmessage(event) {
    const timelineEvent = JSON.parse(event.data);
    setEvents((prev) => [...prev, timelineEvent]);
  },

  onerror(err) {
    console.error('Erreur SSE:', err);
    throw err; // Empêche le retry automatique
  },

  onclose() {
    console.log('Connexion fermée');
  },

  openWhenHidden: false,
}).catch((error) => {
  if (error.name !== 'AbortError') {
    console.error('Erreur fatale:', error);
  }
});

return () => {
  ctrl.abort();
};
```

#### Améliorations clés

1. **Authentification sécurisée**
   - Token envoyé dans le header `Authorization`
   - Plus besoin de passer le token dans l'URL
   - Conforme aux standards de sécurité

2. **Contrôle du cycle de vie**
   - `AbortController` pour annuler proprement la connexion
   - Gestion précise des erreurs avec `onerror`
   - Callback `onclose` pour détecter la fermeture

3. **Pas de retry automatique**
   - `throw err` dans `onerror` empêche le retry
   - `openWhenHidden: false` désactive les reconnexions automatiques
   - Meilleur contrôle pour gérer les erreurs 401/403

4. **Meilleure gestion des erreurs**
   - Distinction entre erreurs fatales et annulations volontaires
   - Filtre `error.name !== 'AbortError'` pour ignorer les annulations normales
   - Logs plus clairs pour le debugging

### 3. Correction du bug i18n

**Fichiers** : `frontend/messages/en.json`, `frontend/messages/fr.json`

Ajout de la clé manquante `status.approvalRequired` :

```json
{
  "status": {
    "approvalRequired": "Approval required for the ImpactPlan"
  }
}
```

**Version française** :
```json
{
  "status": {
    "approvalRequired": "Approbation requise pour l'ImpactPlan"
  }
}
```

### 4. Correction ESLint

**Fichier** : `frontend/components/TimelineDisplay.tsx`

Échappement de l'apostrophe dans le texte français :
```tsx
// Avant
<p>En attente d'événements...</p>

// Après
<p>En attente d&apos;événements...</p>
```

## Tests de validation

### Test 1 : Vérifier l'authentification
**Objectif** : S'assurer que le token est bien envoyé dans les headers

**Procédure** :
1. Lancer le frontend : `npm run dev`
2. Ouvrir DevTools > Network
3. Se connecter et créer une session timeline
4. Observer la requête SSE `/api/v1/timeline/stream/...`
5. Vérifier les Request Headers

**Résultat attendu** :
```
Authorization: Bearer eyJhbGc...
Content-Type: text/event-stream
```

### Test 2 : Vérifier la réception des événements
**Objectif** : S'assurer que les événements arrivent en temps réel

**Procédure** :
1. Lancer un workflow
2. Observer l'onglet "EventStream" dans DevTools
3. Vérifier que les événements s'affichent dans l'UI

**Résultat attendu** :
- Les événements apparaissent dans DevTools
- Les événements s'affichent dans le composant TimelineDisplay
- Les pings keep-alive (`: ping`) sont visibles mais ignorés par le frontend

### Test 3 : Vérifier la gestion des erreurs 401
**Objectif** : S'assurer que les erreurs d'authentification sont bien gérées

**Procédure** :
1. Supprimer le token d'authentification dans localStorage
2. Tenter de se connecter au stream SSE
3. Observer les logs de la console

**Résultat attendu** :
- Erreur 401 détectée et loggée
- Pas de retry infini
- Connexion fermée proprement

### Test 4 : Vérifier le cleanup
**Objectif** : S'assurer que la connexion se ferme proprement

**Procédure** :
1. Lancer un workflow
2. Changer de page ou fermer l'onglet
3. Observer les logs du backend

**Résultat attendu** :
```
[TIMELINE_STREAM] Client disconnected from session: {session_id}
```

### Test 5 : Vérifier les traductions
**Objectif** : S'assurer que la clé i18n est bien traduite

**Procédure** :
1. Lancer un workflow qui nécessite une approbation
2. Observer le message affiché

**Résultat attendu** :
- En anglais : "Approval required for the ImpactPlan"
- En français : "Approbation requise pour l'ImpactPlan"
- Pas de message de warning dans la console

## Compatibilité

### Navigateurs supportés
- ✅ Chrome/Edge (fetch + AbortController natifs)
- ✅ Firefox (fetch + AbortController natifs)
- ✅ Safari (fetch + AbortController natifs)
- ✅ Tous navigateurs modernes avec support ES2020+

### Backend
- ✅ Compatible avec le backend FastAPI existant
- ✅ Utilise le même format SSE (`data: {...}\n\n`)
- ✅ Support des pings keep-alive (`: ping\n\n`)

## Avantages par rapport à EventSource natif

| Critère | EventSource natif | @microsoft/fetch-event-source |
|---------|-------------------|-------------------------------|
| Headers personnalisés | ❌ Non | ✅ Oui |
| Authentification Bearer | ⚠️ URL uniquement | ✅ Header |
| Contrôle du retry | ❌ Non | ✅ Oui |
| AbortController | ❌ Non | ✅ Oui |
| Gestion d'erreur | ⚠️ Basique | ✅ Avancée |
| Callbacks | ⚠️ Limités | ✅ Complets |
| Sécurité | ⚠️ Token dans URL | ✅ Token dans header |

## Bonnes pratiques

### 1. Toujours utiliser AbortController
```typescript
const ctrl = new AbortController();
// ... fetchEventSource avec signal: ctrl.signal
return () => ctrl.abort();
```

### 2. Gérer les erreurs proprement
```typescript
onerror(err) {
  console.error('Erreur SSE:', err);
  throw err; // Empêche le retry infini
}
```

### 3. Filtrer les AbortError
```typescript
.catch((error) => {
  if (error.name !== 'AbortError') {
    console.error('Erreur fatale:', error);
  }
});
```

### 4. Désactiver openWhenHidden si nécessaire
```typescript
openWhenHidden: false, // Pas de reconnexion si onglet caché
```

## Débogage

### Logs à surveiller

**Frontend (console)** :
```
[TIMELINE_STREAM] Connexion fermée pour la session: {session_id}
Erreur de connexion SSE: {error}
Erreur fatale dans le stream SSE: {error}
```

**Backend (logs)** :
```
[TIMELINE_STREAM] Client connected for session: {session_id}
[TIMELINE_STREAM] Sending event #N to session {session_id}: {event_type}
[TIMELINE_STREAM] Sending keep-alive ping #N to session {session_id}
[TIMELINE_STREAM] Stream completed for session {session_id} with X events and Y pings
```

### Problèmes courants

#### 1. Erreur 401 malgré le token
**Cause** : Token expiré ou invalide
**Solution** : Vérifier la validité du token dans localStorage

#### 2. Événements ne s'affichent pas
**Cause** : Parser JSON échoue
**Solution** : Vérifier que `event.data` est du JSON valide

#### 3. Connexion se ferme immédiatement
**Cause** : Erreur dans `onerror` qui throw
**Solution** : Vérifier les logs d'erreur dans la console

#### 4. Fuites mémoire
**Cause** : AbortController non appelé dans cleanup
**Solution** : Toujours appeler `ctrl.abort()` dans le return de useEffect

## Conclusion

La migration vers `@microsoft/fetch-event-source` résout définitivement les problèmes d'authentification SSE et améliore significativement la robustesse du système de timeline en temps réel. L'implémentation est plus sécurisée, plus contrôlable et plus conforme aux standards modernes du web.
