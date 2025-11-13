"""Authentication schemas for Agent4BA."""

from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    """Requête d'inscription d'un nouvel utilisateur."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Nom d'utilisateur (3-50 caractères)",
    )
    password: str = Field(
        ...,
        min_length=6,
        description="Mot de passe (minimum 6 caractères)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "john_doe",
                    "password": "securePassword123",
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """Réponse contenant les informations publiques de l'utilisateur."""

    id: str = Field(..., description="Identifiant unique de l'utilisateur")
    username: str = Field(..., description="Nom d'utilisateur")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "username": "john_doe",
                }
            ]
        }
    }


class UserLoginRequest(BaseModel):
    """Requête de connexion."""

    username: str = Field(..., description="Nom d'utilisateur")
    password: str = Field(..., description="Mot de passe")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "john_doe",
                    "password": "securePassword123",
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """Réponse contenant le token d'accès JWT."""

    access_token: str = Field(..., description="Token JWT d'accès")
    token_type: str = Field(default="bearer", description="Type de token")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class TokenData(BaseModel):
    """Données extraites du token JWT."""

    username: str | None = None
