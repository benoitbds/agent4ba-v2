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
