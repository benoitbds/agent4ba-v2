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
