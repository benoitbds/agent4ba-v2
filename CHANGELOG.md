# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Non publié]

### Ajouté (2025-11-13)

- **Tests unitaires - fixtures corrigées & module auth validé**
  - Création du fichier `tests/conftest.py` avec fixtures pytest centralisées
  - Fixtures `temp_user_storage`, `client`, `registered_user`, `auth_token` pour les tests d'authentification
  - Fixtures `test_case`, `graph`, `registry` pour les autres modules
  - Configuration pytest dans `pyproject.toml` pour exécuter uniquement les tests du dossier `tests/`

### Modifié (2025-11-13)

- **Refactorisation des tests d'authentification**
  - Suppression des fixtures dupliquées dans `tests/test_auth_register.py`
  - Suppression des fixtures dupliquées dans `tests/test_auth_login.py`
  - Suppression des fixtures dupliquées dans `tests/test_projects_auth.py`
  - Utilisation des fixtures centralisées de `tests/conftest.py`
  - Amélioration de la stratégie de monkey patching pour utiliser l'instance `user_service` du module auth

### Corrigé (2025-11-13)

- **Tests d'authentification**
  - Correction du problème de fixtures non trouvées pour les tests
  - Correction du stockage JSON des utilisateurs (isolation complète entre tests)
  - Correction du test `test_register_password_is_hashed` qui ne trouvait pas l'utilisateur
  - Tous les tests d'authentification passent maintenant (20/20 ✓)
  - Isolation complète des tests avec fichiers temporaires pour chaque test

### Documentation (2025-11-13)

- Mise à jour de `README.md` avec section détaillée sur les tests unitaires
- Ajout de la description des suites de tests (inscription, login, routes protégées)
- Ajout du statut des tests dans le README
- Création de ce fichier CHANGELOG.md

## [0.1.0] - Date antérieure

### Ajouté

- Implémentation initiale de l'authentification JWT
- Module de gestion des utilisateurs avec hashage bcrypt
- Endpoints d'authentification (`/auth/register`, `/auth/login`)
- Routes protégées avec middleware JWT
- Service de stockage des utilisateurs en JSON
- Workflow LangGraph avec classification d'intentions
- Système de gestion de backlog versionné
- API FastAPI avec documentation Swagger/ReDoc
