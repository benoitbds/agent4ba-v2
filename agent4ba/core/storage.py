"""Storage service for project context and backlog management."""

from typing import Any


class ProjectContextService:
    """Service de gestion du contexte et du stockage des projets."""

    def load_context(self, project_id: str) -> dict[str, Any]:
        """
        Charge le contexte d'un projet depuis le stockage.

        Args:
            project_id: Identifiant unique du projet

        Returns:
            Dictionnaire contenant le contexte du projet

        Raises:
            NotImplementedError: Méthode non encore implémentée
        """
        raise NotImplementedError("load_context sera implémenté dans une future itération")

    def save_backlog(self, project_id: str, data: list[dict[str, Any]]) -> None:
        """
        Sauvegarde le backlog d'un projet dans le stockage.

        Args:
            project_id: Identifiant unique du projet
            data: Liste des work items du backlog

        Raises:
            NotImplementedError: Méthode non encore implémentée
        """
        raise NotImplementedError("save_backlog sera implémenté dans une future itération")
