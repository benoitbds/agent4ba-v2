"""Storage service for project context and backlog management."""

import json
import re
from pathlib import Path

from agent4ba.core.models import WorkItem


class ProjectContextService:
    """Service de gestion du contexte et du stockage des projets."""

    def __init__(self, base_path: str = "agent4ba/data/projects") -> None:
        """
        Initialise le service de contexte.

        Args:
            base_path: Chemin de base pour le stockage des projets
        """
        self.base_path = Path(base_path)

    def _get_project_dir(self, project_id: str) -> Path:
        """
        Retourne le chemin du répertoire d'un projet.

        Args:
            project_id: Identifiant unique du projet

        Returns:
            Path vers le répertoire du projet
        """
        return self.base_path / project_id

    def _find_latest_backlog_version(self, project_id: str) -> int | None:
        """
        Trouve le numéro de version le plus élevé du backlog.

        Args:
            project_id: Identifiant unique du projet

        Returns:
            Numéro de version le plus élevé, ou None si aucun backlog n'existe
        """
        project_dir = self._get_project_dir(project_id)
        if not project_dir.exists():
            return None

        versions = []
        for file in project_dir.glob("backlog_v*.json"):
            match = re.match(r"backlog_v(\d+)\.json", file.name)
            if match:
                versions.append(int(match.group(1)))

        return max(versions) if versions else None

    def load_context(self, project_id: str) -> list[WorkItem]:
        """
        Charge le contexte d'un projet depuis le stockage.

        Args:
            project_id: Identifiant unique du projet

        Returns:
            Liste des work items du backlog

        Raises:
            FileNotFoundError: Si le répertoire ou aucun backlog n'existe
        """
        project_dir = self._get_project_dir(project_id)
        if not project_dir.exists():
            raise FileNotFoundError(
                f"Le répertoire du projet '{project_id}' n'existe pas: {project_dir}"
            )

        latest_version = self._find_latest_backlog_version(project_id)
        if latest_version is None:
            raise FileNotFoundError(
                f"Aucun fichier backlog trouvé pour le projet '{project_id}'"
            )

        backlog_file = project_dir / f"backlog_v{latest_version}.json"
        with backlog_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return [WorkItem(**item) for item in data]

    def save_backlog(self, project_id: str, data: list[WorkItem]) -> None:
        """
        Sauvegarde le backlog d'un projet dans le stockage.

        Args:
            project_id: Identifiant unique du projet
            data: Liste des work items du backlog
        """
        project_dir = self._get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        latest_version = self._find_latest_backlog_version(project_id)
        next_version = (latest_version + 1) if latest_version is not None else 1

        backlog_file = project_dir / f"backlog_v{next_version}.json"

        # Convertir les WorkItems en dictionnaires
        data_dicts = [item.model_dump() for item in data]

        with backlog_file.open("w", encoding="utf-8") as f:
            json.dump(data_dicts, f, indent=2, ensure_ascii=False)

    def save_timeline_events(self, project_id: str, events: list[dict]) -> None:
        """
        Sauvegarde les événements de timeline dans l'historique du projet.

        Args:
            project_id: Identifiant unique du projet
            events: Liste des événements de la timeline à ajouter
        """
        project_dir = self._get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        timeline_file = project_dir / "timeline_history.json"

        # Charger l'historique existant
        history = []
        if timeline_file.exists():
            with timeline_file.open("r", encoding="utf-8") as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError:
                    # Si le fichier est corrompu, on repart de zéro
                    history = []

        # Ajouter la nouvelle session avec timestamp
        from datetime import datetime

        session_entry = {
            "timestamp": datetime.now().isoformat(),
            "events": events,
        }
        history.append(session_entry)

        # Sauvegarder l'historique mis à jour
        with timeline_file.open("w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def load_timeline_history(self, project_id: str) -> list[dict]:
        """
        Charge l'historique complet des événements de timeline d'un projet.

        Args:
            project_id: Identifiant unique du projet

        Returns:
            Liste des sessions d'événements avec leurs timestamps

        Raises:
            FileNotFoundError: Si le fichier d'historique n'existe pas
        """
        project_dir = self._get_project_dir(project_id)
        timeline_file = project_dir / "timeline_history.json"

        if not timeline_file.exists():
            # Retourner une liste vide plutôt qu'une erreur
            # (pas d'historique pour un nouveau projet)
            return []

        with timeline_file.open("r", encoding="utf-8") as f:
            try:
                history = json.load(f)
                return history if isinstance(history, list) else []
            except json.JSONDecodeError:
                # Si le fichier est corrompu, retourner une liste vide
                return []

    def delete_project_data(self, project_id: str) -> None:
        """
        Supprime toutes les données associées à un projet.

        Args:
            project_id: Identifiant unique du projet

        Raises:
            FileNotFoundError: Si le projet n'existe pas
            ValueError: Si le project_id contient des caractères dangereux
        """
        # Validation de sécurité : empêcher les attaques de type path traversal
        # Vérifier que le project_id ne contient que des caractères alphanumériques,
        # tirets, underscores et points
        if not re.match(r'^[a-zA-Z0-9._-]+$', project_id):
            raise ValueError(
                f"Invalid project_id '{project_id}': "
                "only alphanumeric characters, dots, hyphens and underscores are allowed"
            )

        # Vérifier qu'il n'y a pas de séquences dangereuses
        if '..' in project_id or project_id.startswith('/') or project_id.startswith('\\'):
            raise ValueError(
                f"Invalid project_id '{project_id}': "
                "path traversal attempts are not allowed"
            )

        project_dir = self._get_project_dir(project_id)

        # Vérifier que le répertoire existe
        if not project_dir.exists():
            raise FileNotFoundError(
                f"Project directory '{project_id}' does not exist: {project_dir}"
            )

        # Vérification de sécurité finale : s'assurer que le chemin résolu
        # est bien un sous-répertoire de base_path
        try:
            resolved_project_dir = project_dir.resolve()
            resolved_base_path = self.base_path.resolve()

            # Vérifier que le projet est bien dans le répertoire de base
            if not str(resolved_project_dir).startswith(str(resolved_base_path)):
                raise ValueError(
                    f"Security violation: project directory '{resolved_project_dir}' "
                    f"is not within base path '{resolved_base_path}'"
                )
        except Exception as e:
            raise ValueError(f"Error resolving project path: {e}") from e

        # Supprimer le répertoire et tout son contenu
        import shutil
        shutil.rmtree(project_dir)

    def create_project(self, project_id: str, creator_user_id: str) -> None:
        """
        Crée un nouveau projet et associe automatiquement l'utilisateur créateur.

        Args:
            project_id: Identifiant unique du projet
            creator_user_id: ID de l'utilisateur qui crée le projet

        Raises:
            ValueError: Si le projet existe déjà
        """
        project_dir = self._get_project_dir(project_id)

        if project_dir.exists():
            raise ValueError(f"Project '{project_id}' already exists")

        # Créer le répertoire du projet
        project_dir.mkdir(parents=True, exist_ok=True)

        # Initialiser un backlog vide
        self.save_backlog(project_id, [])

        # Créer le fichier de gestion des utilisateurs du projet
        users_file = project_dir / "users.json"
        users_data = {
            "project_id": project_id,
            "user_ids": [creator_user_id],
        }

        with users_file.open("w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)

    def add_user_to_project(self, project_id: str, user_id: str) -> None:
        """
        Ajoute un utilisateur à un projet.

        Args:
            project_id: Identifiant unique du projet
            user_id: ID de l'utilisateur à ajouter

        Raises:
            FileNotFoundError: Si le projet n'existe pas
        """
        project_dir = self._get_project_dir(project_id)

        if not project_dir.exists():
            raise FileNotFoundError(f"Project '{project_id}' does not exist")

        users_file = project_dir / "users.json"

        # Charger les utilisateurs existants
        if users_file.exists():
            with users_file.open("r", encoding="utf-8") as f:
                users_data = json.load(f)
        else:
            users_data = {"project_id": project_id, "user_ids": []}

        # Ajouter l'utilisateur s'il n'est pas déjà présent
        if user_id not in users_data["user_ids"]:
            users_data["user_ids"].append(user_id)

        # Sauvegarder
        with users_file.open("w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)

    def remove_user_from_project(self, project_id: str, user_id: str) -> None:
        """
        Retire un utilisateur d'un projet.

        Args:
            project_id: Identifiant unique du projet
            user_id: ID de l'utilisateur à retirer

        Raises:
            FileNotFoundError: Si le projet n'existe pas
            ValueError: Si l'utilisateur n'est pas membre du projet
        """
        project_dir = self._get_project_dir(project_id)

        if not project_dir.exists():
            raise FileNotFoundError(f"Project '{project_id}' does not exist")

        users_file = project_dir / "users.json"

        if not users_file.exists():
            raise FileNotFoundError(f"No users file found for project '{project_id}'")

        # Charger les utilisateurs existants
        with users_file.open("r", encoding="utf-8") as f:
            users_data = json.load(f)

        # Retirer l'utilisateur
        if user_id not in users_data["user_ids"]:
            raise ValueError(f"User '{user_id}' is not a member of project '{project_id}'")

        users_data["user_ids"].remove(user_id)

        # Sauvegarder
        with users_file.open("w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)

    def is_user_authorized_for_project(self, project_id: str, user_id: str) -> bool:
        """
        Vérifie si un utilisateur est autorisé à accéder à un projet.

        Args:
            project_id: Identifiant unique du projet
            user_id: ID de l'utilisateur

        Returns:
            True si l'utilisateur est autorisé, False sinon
        """
        project_dir = self._get_project_dir(project_id)

        if not project_dir.exists():
            return False

        users_file = project_dir / "users.json"

        if not users_file.exists():
            return False

        # Charger les utilisateurs du projet
        with users_file.open("r", encoding="utf-8") as f:
            users_data = json.load(f)

        return user_id in users_data.get("user_ids", [])

    def get_project_users(self, project_id: str) -> list[str]:
        """
        Récupère la liste des IDs des utilisateurs d'un projet.

        Args:
            project_id: Identifiant unique du projet

        Returns:
            Liste des IDs des utilisateurs du projet

        Raises:
            FileNotFoundError: Si le projet n'existe pas
        """
        project_dir = self._get_project_dir(project_id)

        if not project_dir.exists():
            raise FileNotFoundError(f"Project '{project_id}' does not exist")

        users_file = project_dir / "users.json"

        if not users_file.exists():
            return []

        # Charger les utilisateurs du projet
        with users_file.open("r", encoding="utf-8") as f:
            users_data = json.load(f)

        return users_data.get("user_ids", [])

    def update_work_item_in_backlog(
        self, project_id: str, item_id: str, updated_data: dict
    ) -> WorkItem:
        """
        Met à jour un WorkItem dans le backlog d'un projet.

        Args:
            project_id: Identifiant unique du projet
            item_id: Identifiant du WorkItem à mettre à jour
            updated_data: Données partielles à mettre à jour (title, description, etc.)

        Returns:
            Le WorkItem mis à jour

        Raises:
            FileNotFoundError: Si le projet ou le WorkItem n'existe pas
        """
        # Charger le backlog existant
        work_items = self.load_context(project_id)

        # Trouver l'item correspondant
        item_index = None
        for idx, item in enumerate(work_items):
            if item.id == item_id:
                item_index = idx
                break

        if item_index is None:
            raise FileNotFoundError(
                f"WorkItem '{item_id}' not found in project '{project_id}'"
            )

        # Mettre à jour l'item avec les nouvelles données
        current_item = work_items[item_index]
        item_dict = current_item.model_dump()

        # Mettre à jour uniquement les champs fournis
        for key, value in updated_data.items():
            if key in item_dict:
                item_dict[key] = value

        # Créer un nouveau WorkItem avec les données mises à jour
        updated_item = WorkItem(**item_dict)
        work_items[item_index] = updated_item

        # Sauvegarder le backlog mis à jour
        self.save_backlog(project_id, work_items)

        return updated_item

    def validate_work_item_in_backlog(self, project_id: str, item_id: str) -> WorkItem:
        """
        Valide un WorkItem dans le backlog d'un projet (marque comme validé par un humain).

        Args:
            project_id: Identifiant unique du projet
            item_id: Identifiant du WorkItem à valider

        Returns:
            Le WorkItem validé

        Raises:
            FileNotFoundError: Si le projet ou le WorkItem n'existe pas
        """
        # Charger le backlog existant
        work_items = self.load_context(project_id)

        # Trouver l'item correspondant
        item_index = None
        for idx, item in enumerate(work_items):
            if item.id == item_id:
                item_index = idx
                break

        if item_index is None:
            raise FileNotFoundError(
                f"WorkItem '{item_id}' not found in project '{project_id}'"
            )

        # Mettre à jour le statut de validation
        current_item = work_items[item_index]
        item_dict = current_item.model_dump()
        item_dict["validation_status"] = "human_validated"

        # Créer un nouveau WorkItem avec le statut mis à jour
        validated_item = WorkItem(**item_dict)
        work_items[item_index] = validated_item

        # Sauvegarder le backlog mis à jour
        self.save_backlog(project_id, work_items)

        return validated_item

    def create_work_item_in_backlog(
        self, project_id: str, item_data: dict
    ) -> WorkItem:
        """
        Crée un nouveau WorkItem dans le backlog d'un projet.

        Args:
            project_id: Identifiant unique du projet
            item_data: Données du WorkItem à créer (sans ID)

        Returns:
            Le WorkItem créé

        Raises:
            FileNotFoundError: Si le projet n'existe pas
        """
        # Charger le backlog existant (ou créer un backlog vide si le projet existe)
        try:
            work_items = self.load_context(project_id)
        except FileNotFoundError:
            # Vérifier si le projet existe
            project_dir = self._get_project_dir(project_id)
            if not project_dir.exists():
                raise FileNotFoundError(
                    f"Le projet '{project_id}' n'existe pas"
                )
            work_items = []

        # Générer un nouvel ID séquentiel
        max_id = 0
        for item in work_items:
            # Extraire le numéro de l'ID (format WI-001)
            if item.id.startswith("WI-"):
                try:
                    item_num = int(item.id.split("-")[1])
                    if item_num > max_id:
                        max_id = item_num
                except (IndexError, ValueError):
                    continue

        new_id = f"WI-{max_id + 1:03d}"

        # Créer le nouveau WorkItem avec validation_status = "human_validated"
        new_item_data = {
            "id": new_id,
            "project_id": project_id,
            "validation_status": "human_validated",
            **item_data,
        }

        new_item = WorkItem(**new_item_data)
        work_items.append(new_item)

        # Sauvegarder le backlog mis à jour
        self.save_backlog(project_id, work_items)

        return new_item

    def delete_work_item_from_backlog(self, project_id: str, item_id: str) -> None:
        """
        Supprime un WorkItem du backlog d'un projet.

        Args:
            project_id: Identifiant unique du projet
            item_id: Identifiant du WorkItem à supprimer

        Raises:
            FileNotFoundError: Si le projet ou le WorkItem n'existe pas
        """
        # Charger le backlog existant
        work_items = self.load_context(project_id)

        # Trouver l'item correspondant
        item_index = None
        for idx, item in enumerate(work_items):
            if item.id == item_id:
                item_index = idx
                break

        if item_index is None:
            raise FileNotFoundError(
                f"WorkItem '{item_id}' not found in project '{project_id}'"
            )

        # Supprimer l'item
        work_items.pop(item_index)

        # Sauvegarder le backlog mis à jour
        self.save_backlog(project_id, work_items)
