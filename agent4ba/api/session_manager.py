"""Session manager for handling multi-turn conversations with checkpoint persistence."""

import uuid
from typing import Any

from agent4ba.core.logger import setup_logger

logger = setup_logger(__name__)


class SessionManager:
    """
    Gestionnaire de sessions pour les conversations multi-tours.

    Pour ce MVP, les checkpoints sont stockés en mémoire via un dictionnaire.
    Dans une version future, cela pourrait être remplacé par Redis ou une base de données.
    """

    def __init__(self):
        """Initialise le gestionnaire de sessions avec un stockage en mémoire."""
        self._sessions: dict[str, dict[str, Any]] = {}
        logger.info("[SESSION_MANAGER] Initialized with in-memory storage")

    def create_session(self) -> str:
        """
        Crée une nouvelle session avec un identifiant unique.

        Returns:
            Identifiant unique de la conversation (UUID v4)
        """
        conversation_id = str(uuid.uuid4())
        self._sessions[conversation_id] = {}
        logger.info(f"[SESSION_MANAGER] Created new session: {conversation_id}")
        return conversation_id

    def save_checkpoint(self, conversation_id: str, checkpoint: dict[str, Any]) -> None:
        """
        Sauvegarde le checkpoint d'une conversation.

        Args:
            conversation_id: Identifiant unique de la conversation
            checkpoint: Données du checkpoint à sauvegarder

        Raises:
            ValueError: Si le conversation_id n'existe pas
        """
        if conversation_id not in self._sessions:
            logger.error(f"[SESSION_MANAGER] Session not found: {conversation_id}")
            raise ValueError(f"Session {conversation_id} does not exist")

        self._sessions[conversation_id] = checkpoint
        logger.info(
            f"[SESSION_MANAGER] Saved checkpoint for session {conversation_id}"
            f" (keys: {list(checkpoint.keys())})"
        )

    def get_checkpoint(self, conversation_id: str) -> dict[str, Any]:
        """
        Récupère le checkpoint d'une conversation.

        Args:
            conversation_id: Identifiant unique de la conversation

        Returns:
            Données du checkpoint

        Raises:
            ValueError: Si le conversation_id n'existe pas
        """
        if conversation_id not in self._sessions:
            logger.error(f"[SESSION_MANAGER] Session not found: {conversation_id}")
            raise ValueError(f"Session {conversation_id} does not exist")

        checkpoint = self._sessions[conversation_id]
        logger.info(
            f"[SESSION_MANAGER] Retrieved checkpoint for session {conversation_id}"
            f" (keys: {list(checkpoint.keys())})"
        )
        return checkpoint

    def delete_session(self, conversation_id: str) -> None:
        """
        Supprime une session et son checkpoint.

        Args:
            conversation_id: Identifiant unique de la conversation

        Raises:
            ValueError: Si le conversation_id n'existe pas
        """
        if conversation_id not in self._sessions:
            logger.error(f"[SESSION_MANAGER] Session not found: {conversation_id}")
            raise ValueError(f"Session {conversation_id} does not exist")

        del self._sessions[conversation_id]
        logger.info(f"[SESSION_MANAGER] Deleted session: {conversation_id}")

    def session_exists(self, conversation_id: str) -> bool:
        """
        Vérifie si une session existe.

        Args:
            conversation_id: Identifiant unique de la conversation

        Returns:
            True si la session existe, False sinon
        """
        return conversation_id in self._sessions

    def get_all_sessions(self) -> list[str]:
        """
        Récupère la liste de tous les identifiants de session.

        Returns:
            Liste des identifiants de conversation
        """
        return list(self._sessions.keys())


# Instance globale du gestionnaire de sessions
_session_manager_instance: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """
    Récupère l'instance globale du gestionnaire de sessions (singleton).

    Returns:
        Instance du SessionManager
    """
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance
