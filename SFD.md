# Spécifications Fonctionnelles Détaillées (SFD)
## Agent4BA v2.1

**Version:** 2.1
**Date:** 2025-11-13
**Équipe:** Recette et Qualité

---

## Introduction

Ce document décrit le comportement fonctionnel complet de l'application Agent4BA v2.1, incluant tous les flux nominaux, règles de validation et cas d'erreur. Il est destiné à l'équipe de recette pour garantir une couverture exhaustive des tests.

---

## 1. Domaine : Gestion de l'Espace de Travail

### SF-PROJ-01 : Création d'un projet

#### Flux Nominal

1. L'utilisateur clique sur le bouton "+ Nouveau projet" dans le sélecteur de projets
2. Une modale s'ouvre avec un formulaire de création
3. L'utilisateur saisit un nom de projet dans le champ texte (placeholder : "mon-projet")
4. L'utilisateur clique sur le bouton "Créer"
5. Le frontend valide le format du nom
6. Une requête POST est envoyée à `/projects` avec le payload : `{"project_id": "<nom-saisi>"}`
7. Le backend vérifie que le projet n'existe pas déjà
8. Un répertoire est créé dans `agent4ba/data/projects/<project_id>/`
9. Un backlog vide est initialisé (`backlog_v1.json`)
10. Le backend retourne un code 201 avec : `{"project_id": "<project_id>", "message": "Project created successfully"}`
11. Le frontend affiche un toast de succès : "Projet \"<nom>\" créé avec succès"
12. La modale se ferme
13. Le projet nouvellement créé est automatiquement sélectionné dans la liste déroulante

**Référence code :**
- Frontend : `frontend/components/CreateProjectModal.tsx:21-40`
- Backend : `agent4ba/api/main.py:394-428`

#### Règles de Validation

**Validation Frontend :**
- Le nom du projet ne peut pas être vide (après trim)
  - Message d'erreur : "Le nom du projet est requis" (`createProject.nameRequired`)
  - Référence : `frontend/components/CreateProjectModal.tsx:25-28`

- Le nom du projet doit respecter le format : `/^[a-zA-Z0-9_-]+$/`
  - Seuls les lettres (a-z, A-Z), chiffres (0-9), tirets (-) et underscores (_) sont autorisés
  - Pas d'espaces, pas de caractères spéciaux
  - Message d'erreur : "Le nom du projet ne peut contenir que des lettres, chiffres, tirets et underscores" (`createProject.invalidFormat`)
  - Référence : `frontend/components/CreateProjectModal.tsx:31-35`

**Validation Backend :**
- Vérification de l'unicité du nom de projet
  - Référence : `agent4ba/api/main.py:413-417`

#### Cas d'Erreur

**Erreur 1 : Nom de projet vide**
- Contexte : L'utilisateur tente de créer un projet sans saisir de nom
- Comportement : Message d'erreur affiché en rouge sous le champ de saisie
- Message : "Le nom du projet est requis"
- Référence : `frontend/messages/fr.json:116`

**Erreur 2 : Format de nom invalide**
- Contexte : L'utilisateur saisit un nom contenant des espaces ou caractères spéciaux (ex: "mon projet", "test@123")
- Comportement : Message d'erreur affiché en rouge sous le champ de saisie
- Message : "Le nom du projet ne peut contenir que des lettres, chiffres, tirets et underscores"
- Note : Un hint permanent rappelle la règle : "Utilisez uniquement des lettres, chiffres, tirets (-) et underscores (_)"
- Référence : `frontend/messages/fr.json:117-118`

**Erreur 3 : Projet déjà existant**
- Contexte : L'utilisateur tente de créer un projet avec un nom déjà utilisé
- Comportement : Le backend retourne HTTP 400 avec le message d'erreur
- Message : "Project '<project_id>' already exists"
- Code HTTP : 400
- Référence backend : `agent4ba/api/main.py:413-417`
- Comportement frontend : L'erreur est affichée dans un toast d'erreur

---

### SF-PROJ-02 : Sélection d'un projet

#### Flux Nominal

1. Au chargement de l'application, une requête GET est envoyée à `/projects`
2. Le backend scanne le répertoire `agent4ba/data/projects/` et retourne la liste des sous-répertoires
3. La liste est triée par ordre alphabétique
4. Les projets sont affichés dans une liste déroulante (select HTML)
5. L'utilisateur sélectionne un projet dans la liste déroulante
6. L'événement onChange déclenche le chargement des données du projet :
   - Backlog (`GET /projects/<project_id>/backlog`)
   - Documents (`GET /projects/<project_id>/documents`)
   - Historique de timeline (`GET /projects/<project_id>/timeline`)
7. L'interface se met à jour avec les données du projet sélectionné

**Référence code :**
- Frontend : `frontend/components/ProjectSelector.tsx:31-58`
- Backend liste : `agent4ba/api/main.py:367-391`
- Backend backlog : `agent4ba/api/main.py:461-486`

#### Règles de Validation

- Aucune validation particulière côté frontend (simple sélection)
- Le backend vérifie l'existence du projet lors du chargement du backlog

#### Cas d'Erreur

**Erreur 1 : Aucun projet disponible**
- Contexte : Premier démarrage, aucun projet n'a été créé
- Comportement : La liste déroulante affiche une option unique non sélectionnable
- Message : "Aucun projet disponible"
- Référence : `frontend/messages/fr.json:11`

**Erreur 2 : Projet supprimé pendant la session**
- Contexte : Le projet sélectionné a été supprimé (par un autre utilisateur ou manuellement)
- Comportement : Lors de la tentative de chargement du backlog, le backend retourne HTTP 404
- Message : "Backlog not found for project '<project_id>': ..."
- Code HTTP : 404
- Référence : `agent4ba/api/main.py:482-486`

**Erreur 3 : Backlog corrompu ou absent**
- Contexte : Le fichier backlog_v*.json n'existe pas ou est invalide
- Comportement : Le backend lève une FileNotFoundError
- Message : "Aucun fichier backlog trouvé pour le projet '<project_id>'"
- Code HTTP : 404
- Référence : `agent4ba/core/storage.py:76-79`

---

### SF-PROJ-03 : Suppression d'un projet

#### Flux Nominal

1. L'utilisateur clique sur le bouton icône de corbeille (Trash2) à côté du sélecteur de projet
2. Une modale de confirmation s'ouvre avec :
   - Un message d'avertissement rouge
   - Le nom du projet à supprimer en gras
   - La liste des données qui seront supprimées
3. L'utilisateur clique sur "Confirmer la suppression"
4. Le bouton passe en état "Suppression..." (disabled)
5. Une requête DELETE est envoyée à `/projects/<project_id>`
6. Le backend effectue les validations de sécurité sur le `project_id`
7. Le répertoire `agent4ba/data/projects/<project_id>/` et tout son contenu sont supprimés (via `shutil.rmtree`)
8. Le backend retourne un code HTTP 204 (No Content)
9. Le frontend affiche un toast de succès : "Projet \"<nom>\" supprimé avec succès"
10. La modale se ferme
11. La liste des projets est rechargée
12. Si d'autres projets existent, le premier est sélectionné automatiquement

**Référence code :**
- Frontend : `frontend/components/DeleteProjectModal.tsx:23-33`
- Backend : `agent4ba/api/main.py:431-458`
- Service de suppression : `agent4ba/core/storage.py:174-226`

#### Règles de Validation

**Validation Frontend :**
- Le bouton de suppression est désactivé si :
  - Aucun projet n'est sélectionné
  - La liste de projets est vide
- Référence : `frontend/components/ProjectSelector.tsx:62`

**Validation Backend (Sécurité) :**
- Le `project_id` doit contenir uniquement des caractères alphanumériques, points, tirets et underscores : `/^[a-zA-Z0-9._-]+$/`
  - Référence : `agent4ba/core/storage.py:188-192`

- Le `project_id` ne doit pas contenir de séquences dangereuses (path traversal) :
  - Pas de ".."
  - Ne doit pas commencer par "/" ou "\"
  - Référence : `agent4ba/core/storage.py:195-199`

- Le chemin résolu doit être un sous-répertoire strict de `base_path`
  - Référence : `agent4ba/core/storage.py:209-222`

#### Cas d'Erreur

**Erreur 1 : Projet non trouvé**
- Contexte : Tentative de suppression d'un projet qui n'existe pas (déjà supprimé ou inexistant)
- Comportement : Le backend retourne HTTP 404
- Message : "Project directory '<project_id>' does not exist: <chemin>"
- Code HTTP : 404
- Référence : `agent4ba/api/main.py:449-453` et `agent4ba/core/storage.py:204-207`

**Erreur 2 : project_id invalide (caractères non autorisés)**
- Contexte : Tentative de suppression avec un project_id contenant des caractères spéciaux dangereux
- Comportement : Le backend retourne HTTP 400
- Message : "Invalid project_id '<project_id>': only alphanumeric characters, dots, hyphens and underscores are allowed"
- Code HTTP : 400
- Référence : `agent4ba/api/main.py:454-458` et `agent4ba/core/storage.py:188-192`

**Erreur 3 : Tentative de path traversal**
- Contexte : Tentative de suppression avec un project_id contenant ".." ou commençant par "/"
- Comportement : Le backend retourne HTTP 400
- Message : "Invalid project_id '<project_id>': path traversal attempts are not allowed"
- Code HTTP : 400
- Référence : `agent4ba/core/storage.py:195-199`

**Erreur 4 : Violation de sécurité (chemin hors de base_path)**
- Contexte : Le chemin résolu pointe en dehors du répertoire autorisé
- Comportement : Le backend retourne HTTP 400
- Message : "Security violation: project directory '<resolved_path>' is not within base path '<base_path>'"
- Code HTTP : 400
- Référence : `agent4ba/core/storage.py:216-220`

---

## 2. Domaine : Gestion des Connaissances

### SF-DOC-01 : Ajout d'un document

#### Flux Nominal

1. L'utilisateur clique sur le bouton "+" dans la section "Documents du Projet"
2. Une modale d'upload s'ouvre
3. L'utilisateur clique sur le champ de sélection de fichier ou drag & drop un fichier
4. Le navigateur ouvre le sélecteur de fichiers (filtré pour n'afficher que les PDF grâce à `accept="application/pdf"`)
5. L'utilisateur sélectionne un fichier PDF
6. Le frontend valide :
   - Le type MIME du fichier (doit être `application/pdf`)
   - La taille du fichier (max 50 Mo = 52 428 800 bytes)
7. Si valide, le nom et la taille du fichier s'affichent dans un encadré gris
8. L'utilisateur clique sur "Uploader"
9. Le statut passe à "uploading" et le bouton affiche "Upload en cours..."
10. Une requête POST multipart/form-data est envoyée à `/projects/<project_id>/documents`
11. Le backend :
    - Vérifie le content-type (doit être `application/pdf`)
    - Sauvegarde le fichier dans `agent4ba/data/projects/<project_id>/documents/<filename>`
    - Lance la vectorisation automatique du document (extraction de chunks, embedding, indexation FAISS)
12. Le backend retourne HTTP 201 avec :
    ```json
    {
      "filename": "<nom-fichier>",
      "message": "Fichier '<nom-fichier>' uploadé et vectorisé avec succès",
      "vectorization": {
        "num_chunks": <nombre>,
        "num_pages": <nombre>,
        "status": "success"
      }
    }
    ```
13. Le frontend affiche le message de succès en vert pendant 1,5 seconde
14. La modale se ferme automatiquement
15. La liste des documents est rafraîchie pour afficher le nouveau document

**Référence code :**
- Frontend : `frontend/components/UploadDocumentModal.tsx:53-92`
- Backend : `agent4ba/api/main.py:547-613`

#### Règles de Validation

**Validation Frontend :**

1. **Type de fichier**
   - Seuls les fichiers PDF sont acceptés
   - Vérification du type MIME : `file.type === "application/pdf"`
   - Référence : `frontend/components/UploadDocumentModal.tsx:31-36`

2. **Taille du fichier**
   - Taille maximale : 50 Mo (52 428 800 bytes)
   - Calcul : `const MAX_FILE_SIZE = 50 * 1024 * 1024`
   - Référence : `frontend/components/UploadDocumentModal.tsx:38-45`

3. **Fichier sélectionné**
   - Un fichier doit être sélectionné avant de pouvoir cliquer sur "Uploader"
   - Le bouton est désactivé (`disabled`) si `!selectedFile`
   - Référence : `frontend/components/UploadDocumentModal.tsx:54-57`

**Validation Backend :**

1. **Type de contenu**
   - Le content-type HTTP doit être `application/pdf`
   - Référence : `agent4ba/api/main.py:566-573`

#### Cas d'Erreur

**Erreur 1 : Fichier non-PDF**
- Contexte : L'utilisateur tente d'uploader un fichier qui n'est pas un PDF (ex: .docx, .txt)
- Comportement : Validation frontend immédiate
- Affichage : Message d'erreur rouge dans la modale
- Message : "Seuls les fichiers PDF sont acceptés (taille maximale : 50 Mo)"
- Le fichier n'est pas sélectionné (reste null)
- Référence : `frontend/messages/fr.json:140`

**Erreur 2 : Fichier trop volumineux (>50 Mo)**
- Contexte : L'utilisateur sélectionne un fichier PDF de plus de 50 Mo
- Comportement : Validation frontend immédiate
- Affichage : Message d'erreur rouge dans la modale
- Message : "Le fichier dépasse la taille maximale autorisée de 50 Mo."
- Le fichier n'est pas sélectionné (reste null)
- Référence : `frontend/messages/fr.json:145`

**Erreur 3 : Aucun fichier sélectionné**
- Contexte : L'utilisateur clique sur "Uploader" sans avoir sélectionné de fichier (cas edge, normalement le bouton est désactivé)
- Comportement : Validation frontend
- Affichage : Message d'erreur rouge dans la modale
- Message : "Veuillez sélectionner un fichier"
- Référence : `frontend/messages/fr.json:146`

**Erreur 4 : Type de fichier non supporté (backend)**
- Contexte : Le content-type HTTP reçu par le backend n'est pas `application/pdf`
- Comportement : Le backend retourne HTTP 400
- Message : "Type de fichier non supporté: <content-type>. Seuls les fichiers PDF sont acceptés."
- Code HTTP : 400
- Affichage frontend : Toast d'erreur avec le message du backend
- Référence : `agent4ba/api/main.py:566-573`

**Erreur 5 : Erreur lors de la vectorisation**
- Contexte : L'upload réussit mais la vectorisation échoue (document corrompu, erreur PDF, etc.)
- Comportement :
  - Le backend supprime le fichier uploadé (`file_path.unlink()`)
  - Le backend retourne HTTP 500
- Message : "Erreur lors de l'upload ou de la vectorisation du fichier: <détail-erreur>"
- Code HTTP : 500
- Affichage frontend : Toast d'erreur
- Référence : `agent4ba/api/main.py:606-613`

**Erreur 6 : Fichier trop volumineux (HTTP 413)**
- Contexte : Le serveur rejette la requête car elle dépasse la limite de taille configurée (nginx, uvicorn)
- Comportement : Le frontend intercepte le code 413
- Message : "Le fichier dépasse la taille maximale autorisée de 50 Mo."
- Code HTTP : 413
- Référence : `frontend/lib/api.ts:224-227`

**Erreur 7 : Erreur générique d'upload**
- Contexte : Erreur réseau, timeout, ou autre erreur non spécifiée
- Comportement : Le frontend affiche un message générique
- Message : "Erreur lors de l'upload du fichier"
- Référence : `frontend/messages/fr.json:147`

---

### SF-DOC-02 : Suppression d'un document

#### Flux Nominal

1. L'utilisateur visualise la liste des documents dans la section "Documents du Projet"
2. Chaque document dispose d'un bouton de suppression (icône corbeille, visible au survol ou toujours visible selon l'implémentation)
3. L'utilisateur clique sur le bouton de suppression d'un document
4. Une confirmation est demandée (modale ou bouton de confirmation)
5. L'utilisateur confirme la suppression
6. Une requête DELETE est envoyée à `/projects/<project_id>/documents/<document_name>` (avec URLencoding du nom)
7. Le backend :
   - Vérifie que le projet existe
   - Utilise le service `DocumentIngestionService` pour supprimer :
     - Le fichier physique dans `documents/`
     - Les chunks et vecteurs associés dans la base FAISS
     - Met à jour et sauvegarde l'index FAISS
8. Le backend retourne HTTP 204 (No Content)
9. La liste des documents est rafraîchie pour retirer le document supprimé

**Référence code :**
- Backend : `agent4ba/api/main.py:616-667`

#### Règles de Validation

**Validation Backend (Sécurité) :**
- Le `document_name` est validé par le service `DocumentIngestionService` pour éviter les path traversal
- Le projet doit exister
- Le document doit exister dans le répertoire du projet

#### Cas d'Erreur

**Erreur 1 : Projet non trouvé**
- Contexte : Tentative de suppression d'un document dans un projet qui n'existe pas
- Comportement : Le backend retourne HTTP 404
- Message : "Project '<project_id>' not found"
- Code HTTP : 404
- Référence : `agent4ba/api/main.py:642-646`

**Erreur 2 : Document non trouvé**
- Contexte : Tentative de suppression d'un document qui n'existe pas (déjà supprimé ou nom incorrect)
- Comportement : Le backend retourne HTTP 404
- Message : "Document '<document_name>' not found in project '<project_id>': <détail>"
- Code HTTP : 404
- Affichage frontend : Message d'erreur dans un toast
- Message frontend : "Erreur lors de la suppression du document"
- Référence : `agent4ba/api/main.py:653-657` et `frontend/messages/fr.json:43`

**Erreur 3 : document_name invalide (path traversal)**
- Contexte : Tentative de suppression avec un nom de document contenant ".." ou "/"
- Comportement : Le backend retourne HTTP 400
- Message : "Invalid document_name: <détail>"
- Code HTTP : 400
- Référence : `agent4ba/api/main.py:658-662`

**Erreur 4 : Erreur lors de la suppression (autre)**
- Contexte : Erreur d'I/O, permissions, ou autre erreur système
- Comportement : Le backend retourne HTTP 500
- Message : "Error deleting document '<document_name>': <détail>"
- Code HTTP : 500
- Référence : `agent4ba/api/main.py:663-667`

---

### SF-DOC-03 : Visualisation de la liste des documents

#### Flux Nominal

1. Lors de la sélection d'un projet, une requête GET est envoyée à `/projects/<project_id>/documents`
2. Le backend scanne le répertoire `agent4ba/data/projects/<project_id>/documents/`
3. Le backend retourne la liste des noms de fichiers triée alphabétiquement
4. Le frontend affiche chaque document avec :
   - Une icône PDF rouge
   - Le nom du fichier
   - Un bouton pour sélectionner le document comme contexte
   - Un bouton pour supprimer le document
5. Si aucun document n'existe, un message informatif est affiché

**Référence code :**
- Backend : `agent4ba/api/main.py:515-544`
- Frontend : `frontend/components/DocumentManager.tsx:52-91`

#### Règles de Validation

- Le répertoire `documents/` est créé automatiquement s'il n'existe pas
- Seuls les fichiers (pas les répertoires) sont listés

#### Cas d'Erreur

**Erreur 1 : Aucun document disponible**
- Contexte : Le projet ne contient aucun document uploadé
- Comportement : Affichage d'un message informatif (pas une erreur)
- Message : "Pour commencer, ajoutez un document en cliquant sur le bouton +"
- Référence : `frontend/messages/fr.json:37`

**Erreur 2 : Projet non trouvé**
- Contexte : Tentative de liste des documents d'un projet qui n'existe pas
- Comportement : Le répertoire est créé automatiquement (pas d'erreur levée)
- Une liste vide est retournée
- Référence : `agent4ba/api/main.py:533`

---

## 3. Domaine : Interaction avec l'Agent

### SF-CHAT-01 : Soumission d'une requête simple

#### Flux Nominal

1. L'utilisateur saisit une question dans le champ de saisie (ex: "Quelles sont les exigences de sécurité ?")
2. L'utilisateur clique sur "Envoyer" ou appuie sur Entrée
3. Le champ de saisie se vide et passe en état désactivé
4. Le statut affiche "Traitement en cours..."
5. Une requête POST est envoyée à `/chat` avec :
   ```json
   {
     "project_id": "<project_id>",
     "query": "<question-utilisateur>",
     "context": []
   }
   ```
6. Le backend démarre un stream SSE (Server-Sent Events)
7. Le premier événement est `thread_id` contenant l'identifiant de la conversation
8. Le deuxième événement est `user_request` contenant la requête de l'utilisateur
9. Le workflow LangGraph s'exécute et envoie des événements en temps réel :
   - `agent_start` : Démarrage d'un agent avec sa pensée
   - `tool_used` : Utilisation d'un outil (récupération de documents, analyse INVEST, etc.)
   - `agent_plan` : Plan d'action de l'agent
10. Le dernier événement est soit :
    - `workflow_complete` : Workflow terminé avec succès
    - `impact_plan_ready` : En attente d'approbation utilisateur
    - `error` : Erreur survenue
11. Les événements sont sauvegardés dans `timeline_history.json`
12. Le champ de saisie redevient actif
13. Le résultat est affiché dans la timeline

**Référence code :**
- Frontend : `frontend/components/ChatInput.tsx:15-21`
- Backend : `agent4ba/api/main.py:282-301` (endpoint)
- Stream : `agent4ba/api/main.py:55-280` (générateur d'événements)

#### Règles de Validation

**Validation Frontend :**
- La requête ne peut pas être vide (après trim)
- Le bouton "Envoyer" est désactivé si la requête est vide ou pendant le traitement
- Référence : `frontend/components/ChatInput.tsx:17-20`

#### Cas d'Erreur

**Erreur 1 : Erreur réseau ou timeout**
- Contexte : La connexion au backend échoue ou timeout
- Comportement : Exception levée côté frontend lors de la lecture du stream
- Message : Variable selon la nature de l'erreur (ex: "Failed to fetch")
- Affichage : Message d'erreur dans la zone de statut

**Erreur 2 : Erreur pendant l'exécution du workflow**
- Contexte : Exception non gérée dans le workflow LangGraph
- Comportement :
  - Le générateur SSE capture l'exception
  - Un événement `error` est envoyé au frontend
- Message : "An error occurred during workflow execution"
- Détail : La stack trace de l'erreur
- Les événements sont sauvegardés malgré l'erreur
- Référence : `agent4ba/api/main.py:252-275`

**Erreur 3 : Projet sans documents**
- Contexte : L'utilisateur pose une question mais aucun document n'a été uploadé
- Comportement : Le workflow s'exécute mais peut retourner un résultat indiquant l'absence de contexte
- Ce n'est pas techniquement une erreur, mais une limitation fonctionnelle

---

### SF-CHAT-02 : Soumission d'une requête avec contexte

#### Flux Nominal

1. L'utilisateur sélectionne des éléments de contexte avant de poser sa question :
   - Documents : En cliquant sur le bouton de sélection dans la liste des documents
   - WorkItems : En cliquant sur l'icône ClipboardPlus dans le backlog
2. Les éléments sélectionnés s'affichent sous forme de "pilules" avec :
   - Le type (document ou work_item)
   - L'identifiant ou le nom
   - Un bouton "×" pour retirer du contexte
3. L'utilisateur saisit sa question
4. L'utilisateur clique sur "Envoyer"
5. Une requête POST est envoyée à `/chat` avec :
   ```json
   {
     "project_id": "<project_id>",
     "query": "<question-utilisateur>",
     "context": [
       {"type": "document", "id": "<nom-fichier>"},
       {"type": "work_item", "id": "<item-id>"}
     ]
   }
   ```
6. Le backend utilise le contexte pour cibler spécifiquement :
   - Les documents mentionnés (pour la recherche vectorielle)
   - Les work items mentionnés (pour analyse ou modification)
7. Le workflow s'exécute avec le contexte enrichi
8. Les événements SSE sont streamés comme pour une requête simple

**Référence code :**
- Frontend pilules : `frontend/components/ContextPills.tsx`
- Backend contexte : `agent4ba/api/main.py:93-96`
- Schéma : `agent4ba/api/schemas.py:8-25`

#### Règles de Validation

**Validation Backend :**
- Le champ `context` est optionnel (peut être null ou absent)
- Si présent, chaque item doit avoir :
  - `type` : "document" ou "work_item"
  - `id` : Identifiant de la ressource

#### Cas d'Erreur

**Erreur 1 : Document de contexte supprimé**
- Contexte : Un document est sélectionné dans le contexte puis supprimé avant l'envoi de la requête
- Comportement : Le workflow peut échouer ou ignorer silencieusement le document manquant
- Impact : Dépend de l'implémentation du workflow

**Erreur 2 : WorkItem de contexte supprimé**
- Contexte : Un work item est sélectionné dans le contexte mais n'existe plus dans le backlog
- Comportement : Le workflow peut échouer ou ignorer silencieusement le work item manquant
- Impact : Dépend de l'implémentation du workflow

---

## 4. Domaine : Visualisation et Gestion du Backlog

### SF-BACK-01 : Visualisation du backlog hiérarchique

#### Flux Nominal

1. Lors de la sélection d'un projet, une requête GET est envoyée à `/projects/<project_id>/backlog`
2. Le backend :
   - Trouve la version la plus récente du backlog (`backlog_v<N>.json`)
   - Charge et parse le fichier JSON
   - Retourne la liste des WorkItems
3. Le frontend reçoit la liste plate de WorkItems
4. Le frontend construit une hiérarchie en séparant :
   - Items parents (sans `parent_id`) : Généralement des Features
   - Items enfants (avec `parent_id`) : Généralement des Stories ou Tasks
5. Par défaut, toutes les features sont dépliées (expanded)
6. Pour chaque item, le frontend affiche :
   - Badge coloré du type (feature=violet, story=bleu, task=vert)
   - Titre
   - ID technique (en gris, police monospace)
   - Badge "IA" si `validation_status === "pending_validation"`
   - Description (si présente)
   - Badges INVEST avec code couleur selon le score (si présents)
   - Attributs : priority, points, status
7. Les features affichent un chevron (ChevronDown ou ChevronRight) et le nombre d'enfants
8. Les stories enfants sont indentées avec une marge gauche de 8 unités

**Référence code :**
- Backend : `agent4ba/api/main.py:461-486`
- Frontend hiérarchie : `frontend/components/BacklogView.tsx:38-58`
- Frontend rendu : `frontend/components/BacklogView.tsx:283-473`

#### Règles de Validation

- Un WorkItem est considéré comme parent si `parent_id` est null
- Un WorkItem est considéré comme enfant si `parent_id` est défini

#### Cas d'Erreur

**Erreur 1 : Backlog vide**
- Contexte : Le projet ne contient aucun work item (nouveau projet ou backlog vidé)
- Comportement : Affichage d'un message informatif (pas une erreur)
- Message : "Aucun item dans le backlog"
- Référence : `frontend/messages/fr.json:49`

**Erreur 2 : Backlog non trouvé (projet inexistant)**
- Contexte : Tentative de chargement du backlog d'un projet qui n'existe pas
- Comportement : Le backend retourne HTTP 404
- Message : "Backlog not found for project '<project_id>': Le répertoire du projet '<project_id>' n'existe pas: <chemin>"
- Code HTTP : 404
- Référence : `agent4ba/api/main.py:482-486`

**Erreur 3 : Aucun fichier backlog**
- Contexte : Le répertoire du projet existe mais aucun fichier `backlog_v*.json` n'est présent
- Comportement : Le backend retourne HTTP 404
- Message : "Backlog not found for project '<project_id>': Aucun fichier backlog trouvé pour le projet '<project_id>'"
- Code HTTP : 404
- Référence : `agent4ba/core/storage.py:76-79`

---

### SF-BACK-02 : Repliage/Dépliage des features

#### Flux Nominal

1. L'utilisateur clique sur le chevron d'une feature
2. L'événement `onClick` est intercepté avec `stopPropagation()` pour ne pas déclencher l'édition
3. L'état `expandedItems` (Set) est mis à jour :
   - Si l'ID est dans le Set : il est retiré (feature se replie)
   - Si l'ID n'est pas dans le Set : il est ajouté (feature se déplie)
4. Le re-render affiche ou masque les children selon le nouvel état
5. Animation visuelle :
   - ChevronDown quand déplié
   - ChevronRight quand replié

**Référence code :**
- Frontend : `frontend/components/BacklogView.tsx:84-94`

#### Règles de Validation

- Seules les features (items parents) ont un chevron
- Les stories/tasks enfants ne sont pas repliables individuellement

#### Cas d'Erreur

Aucun cas d'erreur (fonctionnalité purement visuelle côté frontend).

---

### SF-BACK-03 : Édition d'un WorkItem

#### Flux Nominal

1. L'utilisateur clique n'importe où sur la carte d'un WorkItem (feature ou story)
2. Une modale d'édition s'ouvre avec :
   - Le type et l'ID du WorkItem en lecture seule
   - Un champ "Titre" pré-rempli
   - Un champ "Description" (textarea) pré-rempli
3. L'utilisateur modifie le titre et/ou la description
4. L'utilisateur clique sur "Sauvegarder"
5. Validation frontend :
   - Le titre ne peut pas être vide (après trim)
   - Message d'erreur si vide : "Le titre est requis"
6. Le bouton passe en état "Sauvegarde..." (disabled)
7. Une requête PUT est envoyée à `/projects/<project_id>/backlog/<item_id>` avec :
   ```json
   {
     "title": "<nouveau-titre>",
     "description": "<nouvelle-description>"
   }
   ```
8. Le backend :
   - Charge le backlog actuel
   - Trouve le WorkItem par son ID
   - Met à jour les champs fournis (merge partiel)
   - Sauvegarde une nouvelle version du backlog (`backlog_v<N+1>.json`)
9. Le backend retourne HTTP 200 avec le WorkItem mis à jour
10. La modale se ferme
11. Le backlog est rechargé pour afficher les modifications

**Référence code :**
- Frontend : `frontend/components/EditWorkItemModal.tsx:35-61`
- Backend : `agent4ba/api/main.py:670-700`
- Service : `agent4ba/core/storage.py:228-276`

#### Règles de Validation

**Validation Frontend :**
- Le titre est obligatoire (non vide après trim)
- Message d'erreur : "Le titre est requis"
- Référence : `frontend/components/EditWorkItemModal.tsx:39-42`

**Validation Backend :**
- Le projet doit exister
- Le WorkItem doit exister dans le backlog
- Les champs fournis doivent correspondre au schéma WorkItem

#### Cas d'Erreur

**Erreur 1 : Titre vide**
- Contexte : L'utilisateur efface le titre et tente de sauvegarder
- Comportement : Validation frontend bloque la sauvegarde
- Message : "Le titre est requis"
- Affichage : Message d'erreur rouge dans la modale
- Référence : `frontend/messages/fr.json:170`

**Erreur 2 : Projet ou WorkItem non trouvé**
- Contexte : Le projet ou le WorkItem a été supprimé pendant l'édition
- Comportement : Le backend retourne HTTP 404
- Message : "Project or WorkItem not found: <détail>"
- Code HTTP : 404
- Affichage frontend : Message d'erreur dans la modale
- Message frontend : "Erreur lors de la sauvegarde"
- Référence : `agent4ba/api/main.py:691-695` et `frontend/messages/fr.json:176`

**Erreur 3 : Erreur de sauvegarde (autre)**
- Contexte : Erreur d'I/O ou autre erreur système
- Comportement : Le backend retourne HTTP 500
- Message : "Error updating WorkItem '<item_id>': <détail>"
- Code HTTP : 500
- Affichage frontend : "Erreur lors de la sauvegarde"
- Référence : `agent4ba/api/main.py:696-700`

---

## 5. Domaine : Cycle de Vie et Validation

### SF-VAL-01 : Affichage du statut de validation

#### Flux Nominal

1. Lorsqu'un WorkItem est créé par l'IA, il reçoit le statut `validation_status: "pending_validation"`
2. Lors de l'affichage du backlog, le frontend vérifie `item.attributes?.validation_status`
3. Si la valeur est `"pending_validation"`, un badge "IA" s'affiche :
   - Icône : Sparkles (étoiles scintillantes)
   - Couleur : Fond ambre clair, texte ambre foncé, bordure ambre
   - Position : À côté du titre et de l'ID
4. Les WorkItems validés (`validation_status: "human_validated"`) n'affichent pas de badge

**Référence code :**
- Modèle : `agent4ba/core/models.py:20-23`
- Frontend : `frontend/components/BacklogView.tsx:182-187` et `340-345`

#### Règles de Validation

- Le statut par défaut lors de la création d'un WorkItem est `"human_validated"`
- Seule l'IA peut créer des items avec `"pending_validation"`
- Le statut est stocké dans `attributes.validation_status` (pas à la racine du modèle)

#### Cas d'Erreur

Aucun cas d'erreur (affichage conditionnel basé sur un attribut).

---

### SF-VAL-02 : Validation manuelle d'un WorkItem

#### Flux Nominal

1. L'utilisateur visualise le backlog et identifie un WorkItem avec le badge "IA"
2. Un bouton avec l'icône CheckCircle (cercle avec coche) est visible à droite du WorkItem
3. L'utilisateur clique sur le bouton "Valider cet item"
4. L'événement `onClick` est intercepté avec `stopPropagation()` pour ne pas ouvrir la modale d'édition
5. Une requête POST est envoyée à `/projects/<project_id>/backlog/<item_id>/validate`
6. Le backend :
   - Charge le backlog actuel
   - Trouve le WorkItem par son ID
   - Met à jour `attributes.validation_status` à `"human_validated"`
   - Sauvegarde une nouvelle version du backlog (`backlog_v<N+1>.json`)
7. Le backend retourne HTTP 200 avec le WorkItem validé
8. Un toast de succès s'affiche : "L'item \"<titre>\" a été validé avec succès"
9. Le backlog est rechargé
10. Le badge "IA" disparaît et le bouton de validation n'est plus affiché

**Référence code :**
- Frontend : `frontend/components/BacklogView.tsx:118-131`
- Backend : `agent4ba/api/main.py:703-732`
- Service : `agent4ba/core/storage.py:278-319`

#### Règles de Validation

**Validation Backend :**
- Le projet doit exister
- Le WorkItem doit exister dans le backlog
- Le WorkItem peut être validé quel que soit son statut actuel (idempotent)

#### Cas d'Erreur

**Erreur 1 : Projet ou WorkItem non trouvé**
- Contexte : Le projet ou le WorkItem a été supprimé entre l'affichage et la validation
- Comportement : Le backend retourne HTTP 404
- Message : "Project or WorkItem not found: <détail>"
- Code HTTP : 404
- Affichage frontend : Toast d'erreur
- Message frontend : "Erreur lors de la validation de l'item"
- Référence : `agent4ba/api/main.py:723-727` et `frontend/messages/fr.json:57`

**Erreur 2 : Erreur de sauvegarde (autre)**
- Contexte : Erreur d'I/O ou autre erreur système
- Comportement : Le backend retourne HTTP 500
- Message : "Error validating WorkItem '<item_id>': <détail>"
- Code HTTP : 500
- Affichage frontend : Toast d'erreur
- Message frontend : "Erreur lors de la validation de l'item"
- Référence : `agent4ba/api/main.py:728-732`

---

## 6. Domaine Complémentaire : Timeline et Historique

### SF-TIME-01 : Visualisation de la timeline en temps réel

#### Flux Nominal

1. Lors de la soumission d'une requête au chat, le frontend s'abonne au stream SSE
2. Pour chaque événement reçu :
   - `thread_id` : Initialisation de la session
   - `user_request` : Affichage de la requête utilisateur
   - `agent_start` : Affichage du démarrage d'un agent avec sa pensée
   - `tool_used` : Affichage de l'outil utilisé avec description et statut
   - `agent_plan` : Affichage du plan d'action avec liste des étapes
   - `impact_plan_ready` : Affichage de la modale d'approbation
   - `workflow_complete` : Affichage du résultat final
   - `error` : Affichage de l'erreur
3. Chaque événement est affiché dans la timeline avec :
   - Icône appropriée
   - Titre de l'événement
   - Détails (expansibles selon le type)
   - Timestamp
4. Les événements sont affichés en temps réel au fur et à mesure de leur réception

**Référence code :**
- Backend événements : `agent4ba/api/events.py`
- Frontend timeline : `frontend/components/AgentTimeline.tsx`

---

### SF-TIME-02 : Sauvegarde et consultation de l'historique

#### Flux Nominal

1. À la fin de chaque session (succès ou erreur), les événements sont sauvegardés
2. Le backend appelle `storage.save_timeline_events(project_id, timeline_events)`
3. Les événements sont ajoutés à `timeline_history.json` avec un timestamp
4. L'utilisateur peut consulter l'historique via GET `/projects/<project_id>/timeline`
5. L'historique est structuré par session :
   ```json
   [
     {
       "timestamp": "2025-11-13T14:30:00",
       "events": [...]
     }
   ]
   ```

**Référence code :**
- Backend sauvegarde : `agent4ba/api/main.py:245-248` et `266-275`
- Backend lecture : `agent4ba/api/main.py:489-512`
- Service : `agent4ba/core/storage.py:109-172`

---

## 7. Annexes

### A. Codes HTTP utilisés

| Code | Signification | Usage dans l'application |
|------|---------------|--------------------------|
| 200 | OK | Requêtes GET réussies, PUT réussies |
| 201 | Created | Création de projet, upload de document |
| 204 | No Content | Suppression de projet, suppression de document |
| 400 | Bad Request | Validation échouée, paramètres invalides |
| 404 | Not Found | Ressource (projet, document, WorkItem) non trouvée |
| 413 | Content Too Large | Fichier uploadé trop volumineux |
| 500 | Internal Server Error | Erreur serveur non gérée |

### B. Messages d'erreur frontend (fr.json)

Tous les messages affichés à l'utilisateur sont définis dans `frontend/messages/fr.json`. Exemples clés :

- **Projets :**
  - `createProject.nameRequired` : "Le nom du projet est requis"
  - `createProject.invalidFormat` : "Le nom du projet ne peut contenir que des lettres, chiffres, tirets et underscores"

- **Documents :**
  - `uploadDocument.fileTooLarge` : "Le fichier dépasse la taille maximale autorisée de 50 Mo."
  - `uploadDocument.onlyPdf` : "Seuls les fichiers PDF sont acceptés (taille maximale : 50 Mo)"
  - `documents.deleteError` : "Erreur lors de la suppression du document"

- **Backlog :**
  - `backlog.empty` : "Aucun item dans le backlog"
  - `backlog.validationSuccess` : "L'item \"{title}\" a été validé avec succès"
  - `backlog.validationError` : "Erreur lors de la validation de l'item"
  - `editWorkItem.titleRequired` : "Le titre est requis"
  - `editWorkItem.saveFailed` : "Erreur lors de la sauvegarde"

### C. Structure des données WorkItem

```json
{
  "id": "WI-001",
  "project_id": "mon-projet",
  "type": "feature|story|task",
  "title": "Titre du work item",
  "description": "Description détaillée (optionnel)",
  "parent_id": "WI-000 (optionnel)",
  "validation_status": "pending_validation|human_validated",
  "attributes": {
    "priority": "high|medium|low",
    "status": "todo|in_progress|done",
    "points": 8,
    "invest_analysis": {
      "I": {"score": 0.9, "reason": "..."},
      "N": {"score": 0.8, "reason": "..."},
      "V": {"score": 1.0, "reason": "..."},
      "E": {"score": 0.7, "reason": "..."},
      "S": {"score": 0.6, "reason": "..."},
      "T": {"score": 0.9, "reason": "..."}
    }
  }
}
```

### D. Badges INVEST et code couleur

- Score > 0.8 : Vert (`bg-green-500`)
- Score > 0.6 : Orange (`bg-orange-500`)
- Score ≤ 0.6 : Rouge (`bg-red-500`)

**Référence :** `frontend/components/BacklogView.tsx:61-65`

### E. Versioning du backlog

- Format : `backlog_v<N>.json`
- Chaque modification crée une nouvelle version (N+1)
- Seule la version la plus récente est utilisée pour la lecture
- L'historique permet de tracer l'évolution du backlog

**Référence :** `agent4ba/core/storage.py:34-54` et `87-107`

---

## Conclusion

Ce document décrit l'intégralité du comportement fonctionnel de l'application Agent4BA v2.1 tel qu'implémenté dans le code source. Chaque spécification inclut :

- Le flux nominal détaillé
- Les règles de validation frontend et backend
- Les cas d'erreur exhaustifs avec codes HTTP et messages exacts
- Les références aux fichiers source pour traçabilité

Ce document constitue la base pour la rédaction des plans de test et la validation en recette.
