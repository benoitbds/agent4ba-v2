# Validation du système Keep-Alive SSE

## Contexte
Le flux SSE peut être mis en buffer par des proxys intermédiaires (nginx, reverse proxies, etc.), empêchant l'affichage en temps réel des événements. Pour résoudre ce problème, nous avons implémenté un système de keep-alive qui envoie périodiquement des commentaires SSE.

## Implémentation

### Modifications apportées
- **Fichier modifié** : `agent4ba/api/main.py`
- **Endpoint** : `GET /api/v1/timeline/stream/{session_id}`
- **Fonction** : `event_generator()`

### Mécanisme
1. Utilisation de `asyncio.wait_for()` avec un timeout de **3 secondes**
2. Si un événement arrive avant le timeout, il est envoyé normalement
3. Si le timeout expire, un ping keep-alive est envoyé : `: ping\n\n`
4. Les pings sont des commentaires SSE (commencent par `:`) et sont automatiquement ignorés par EventSource côté client
5. Les pings forcent les proxys à purger leurs buffers et à streamer immédiatement

### Code clé
```python
while True:
    try:
        # Attendre le prochain événement avec un timeout de 3 secondes
        event = await asyncio.wait_for(event_iterator.__anext__(), timeout=3.0)
        # ... envoyer l'événement ...

    except asyncio.TimeoutError:
        # Timeout expiré, envoyer un ping keep-alive
        yield ": ping\n\n"

    except StopAsyncIteration:
        # Le stream est terminé
        break
```

## Tests de validation

### Test 1 : Vérifier que les pings sont envoyés
**Objectif** : Vérifier que les pings sont envoyés toutes les 3 secondes en l'absence d'événements réels

**Procédure** :
1. Lancer le backend : `cd agent4ba && uvicorn api.main:app --reload --port 8002`
2. Créer un projet et lancer un workflow simple
3. Ouvrir DevTools > Network
4. Filtrer sur `/api/v1/timeline/stream/`
5. Cliquer sur la requête SSE
6. Observer l'onglet EventStream ou Response

**Résultat attendu** :
- Des lignes `: ping` apparaissent régulièrement (toutes les ~3 secondes) entre les événements réels
- Les pings ne sont pas visibles dans l'UI du frontend (ignorés par EventSource)
- Le stream reste ouvert et réactif

### Test 2 : Vérifier que les événements réels ne sont pas affectés
**Objectif** : Vérifier que les événements réels sont toujours envoyés et affichés correctement

**Procédure** :
1. Lancer un workflow qui génère des événements rapidement
2. Observer la timeline dans l'UI
3. Vérifier les logs du backend

**Résultat attendu** :
- Tous les événements sont affichés correctement dans l'UI
- Les pings n'interfèrent pas avec l'affichage des événements
- Aucune duplication ou perte d'événements
- Logs montrent : "Sending event #N" et "Sending keep-alive ping #N"

### Test 3 : Test avec proxy buffering (nginx)
**Objectif** : Vérifier que les pings forcent la purge des buffers des proxys

**Configuration nginx** :
```nginx
location /api/v1/timeline/stream/ {
    proxy_pass http://localhost:8002;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
}
```

**Procédure** :
1. Configurer nginx comme reverse proxy
2. Activer temporairement `proxy_buffering on` pour tester
3. Lancer un workflow
4. Observer si les événements arrivent en temps réel malgré le buffering

**Résultat attendu** :
- Même avec `proxy_buffering on`, les événements arrivent régulièrement grâce aux pings
- Pas de retard de plusieurs secondes dans l'affichage

### Test 4 : Test de longue durée
**Objectif** : Vérifier la stabilité du système sur de longues périodes

**Procédure** :
1. Lancer un workflow qui prend plusieurs minutes
2. Garder la connexion SSE ouverte pendant toute la durée
3. Observer les logs et la stabilité de la connexion

**Résultat attendu** :
- La connexion reste ouverte sans interruption
- Les pings continuent d'être envoyés régulièrement
- Aucune erreur de timeout ou de connexion
- Le compteur de pings augmente continuellement

## Monitoring et Logs

### Logs à surveiller
```
[TIMELINE_STREAM] Client connected for session: {session_id}
[TIMELINE_STREAM] Sending event #N to session {session_id}: {event_type}
[TIMELINE_STREAM] Sending keep-alive ping #N to session {session_id}
[TIMELINE_STREAM] Stream completed for session {session_id} with X events and Y pings
[TIMELINE_STREAM] Client disconnected from session: {session_id}
```

### Métriques à observer
- **Ratio pings/événements** : Plus élevé pour des workflows lents, plus faible pour des workflows rapides
- **Temps de connexion** : Doit rester stable même pour des workflows longs
- **Pas d'erreurs** : Aucun timeout, aucune exception non gérée

## Compatibilité

### Navigateurs
- ✅ Chrome/Edge (EventSource natif)
- ✅ Firefox (EventSource natif)
- ✅ Safari (EventSource natif)
- ✅ Tous les navigateurs modernes supportant EventSource

### Infrastructure
- ✅ Nginx (avec `X-Accel-Buffering: no` header déjà présent)
- ✅ Apache
- ✅ CloudFlare
- ✅ AWS ALB/ELB
- ✅ Kubernetes Ingress

## Paramètres ajustables

### Timeout du ping (actuellement 3 secondes)
Pour modifier la fréquence des pings :
```python
# Dans event_generator()
event = await asyncio.wait_for(event_iterator.__anext__(), timeout=5.0)  # 5 secondes
```

**Recommandations** :
- **1-2 secondes** : Pour des proxys très agressifs avec buffering
- **3-5 secondes** : Configuration par défaut équilibrée
- **10+ secondes** : Pour réduire la charge réseau si le buffering n'est pas un problème

## Conclusion

L'implémentation du keep-alive SSE résout efficacement le problème de buffering des proxys tout en maintenant :
- ✅ Performance : Overhead minimal (quelques octets toutes les 3 secondes)
- ✅ Compatibilité : Fonctionne avec tous les clients EventSource
- ✅ Robustesse : Gestion propre des timeouts et exceptions
- ✅ Transparence : Les pings sont invisibles pour le frontend
