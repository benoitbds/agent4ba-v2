"""User service for managing user authentication and storage."""

import json
import uuid
from pathlib import Path
from typing import Any

from passlib.context import CryptContext  # type: ignore[import-untyped]

from agent4ba.core.models import User

# Configuration de passlib pour le hashage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """
    Service de gestion des utilisateurs.

    Gère le stockage, la récupération et l'authentification des utilisateurs.
    Pour le MVP, utilise un simple fichier JSON comme base de données.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """
        Initialise le service utilisateur.

        Args:
            storage_path: Chemin du fichier de stockage des utilisateurs.
                         Par défaut: agent4ba/data/users.json
        """
        if storage_path is None:
            # Utiliser le dossier data du projet
            base_path = Path(__file__).parent.parent / "data"
            base_path.mkdir(parents=True, exist_ok=True)
            storage_path = base_path / "users.json"

        self.storage_path = storage_path
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        """Crée le fichier de stockage s'il n'existe pas."""
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def _load_users(self) -> list[dict[str, Any]]:
        """
        Charge tous les utilisateurs depuis le stockage.

        Returns:
            Liste des utilisateurs sous forme de dictionnaires
        """
        try:
            content = self.storage_path.read_text(encoding="utf-8")
            return json.loads(content)  # type: ignore[no-any-return]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_users(self, users: list[dict[str, Any]]) -> None:
        """
        Sauvegarde la liste des utilisateurs dans le stockage.

        Args:
            users: Liste des utilisateurs à sauvegarder
        """
        self.storage_path.write_text(
            json.dumps(users, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_user_by_username(self, username: str) -> User | None:
        """
        Récupère un utilisateur par son nom d'utilisateur.

        Args:
            username: Nom d'utilisateur à rechercher

        Returns:
            L'utilisateur trouvé ou None
        """
        users = self._load_users()
        for user_data in users:
            if user_data["username"] == username:
                return User(**user_data)
        return None

    def get_user_by_id(self, user_id: str) -> User | None:
        """
        Récupère un utilisateur par son ID.

        Args:
            user_id: ID de l'utilisateur à rechercher

        Returns:
            L'utilisateur trouvé ou None
        """
        users = self._load_users()
        for user_data in users:
            if user_data["id"] == user_id:
                return User(**user_data)
        return None

    def create_user(self, username: str, password: str) -> User:
        """
        Crée un nouvel utilisateur.

        Args:
            username: Nom d'utilisateur
            password: Mot de passe en clair (sera hashé)

        Returns:
            L'utilisateur créé

        Raises:
            ValueError: Si le nom d'utilisateur existe déjà
        """
        # Vérifier que l'utilisateur n'existe pas déjà
        if self.get_user_by_username(username) is not None:
            raise ValueError(f"Username '{username}' already exists")

        # Hasher le mot de passe
        hashed_password = pwd_context.hash(password)

        # Créer l'utilisateur
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            hashed_password=hashed_password,
            is_active=True,
            project_ids=[],
        )

        # Sauvegarder
        users = self._load_users()
        users.append(user.model_dump())
        self._save_users(users)

        return user

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Vérifie qu'un mot de passe en clair correspond au hash.

        Args:
            plain_password: Mot de passe en clair
            hashed_password: Mot de passe hashé

        Returns:
            True si le mot de passe correspond, False sinon
        """
        return pwd_context.verify(plain_password, hashed_password)  # type: ignore[no-any-return]

    def authenticate_user(self, username: str, password: str) -> User | None:
        """
        Authentifie un utilisateur avec son nom d'utilisateur et mot de passe.

        Args:
            username: Nom d'utilisateur
            password: Mot de passe en clair

        Returns:
            L'utilisateur si l'authentification réussit, None sinon
        """
        user = self.get_user_by_username(username)
        if user is None:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        return user

    def add_project_to_user(self, user_id: str, project_id: str) -> User:
        """
        Ajoute un projet à la liste des projets d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            project_id: ID du projet à ajouter

        Returns:
            L'utilisateur mis à jour

        Raises:
            ValueError: Si l'utilisateur n'existe pas
        """
        users = self._load_users()
        user_index = None

        for idx, user_data in enumerate(users):
            if user_data["id"] == user_id:
                user_index = idx
                break

        if user_index is None:
            raise ValueError(f"User with id '{user_id}' not found")

        # Ajouter le project_id s'il n'est pas déjà présent
        if "project_ids" not in users[user_index]:
            users[user_index]["project_ids"] = []

        if project_id not in users[user_index]["project_ids"]:
            users[user_index]["project_ids"].append(project_id)

        self._save_users(users)
        return User(**users[user_index])

    def remove_project_from_user(self, user_id: str, project_id: str) -> User:
        """
        Retire un projet de la liste des projets d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            project_id: ID du projet à retirer

        Returns:
            L'utilisateur mis à jour

        Raises:
            ValueError: Si l'utilisateur n'existe pas
        """
        users = self._load_users()
        user_index = None

        for idx, user_data in enumerate(users):
            if user_data["id"] == user_id:
                user_index = idx
                break

        if user_index is None:
            raise ValueError(f"User with id '{user_id}' not found")

        # Retirer le project_id s'il existe
        if "project_ids" in users[user_index] and project_id in users[user_index]["project_ids"]:
            users[user_index]["project_ids"].remove(project_id)

        self._save_users(users)
        return User(**users[user_index])

    def get_user_projects(self, user_id: str) -> list[str]:
        """
        Récupère la liste des projets d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur

        Returns:
            Liste des IDs de projets

        Raises:
            ValueError: Si l'utilisateur n'existe pas
        """
        user = self.get_user_by_id(user_id)
        if user is None:
            raise ValueError(f"User with id '{user_id}' not found")

        return user.project_ids
