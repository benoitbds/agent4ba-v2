"""Authentication endpoints and utilities for Agent4BA."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt  # type: ignore[import-untyped]

from agent4ba.api.schemas_auth import (
    TokenData,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from agent4ba.core.config import settings
from agent4ba.core.models import User
from agent4ba.services.user_service import UserService

# Configuration du logger
logger = logging.getLogger(__name__)

# OAuth2 scheme pour extraire le token du header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Instance du service utilisateur
user_service = UserService()

# Router pour les endpoints d'authentification
router = APIRouter(prefix="/auth", tags=["Authentication"])


def create_access_token(data: dict[str, str], expires_delta: timedelta | None = None) -> str:
    """
    Crée un token JWT d'accès.

    Args:
        data: Données à encoder dans le token (typiquement {"sub": username})
        expires_delta: Durée de validité du token. Si None, utilise la valeur par défaut

    Returns:
        Token JWT encodé
    """
    to_encode: dict[str, str | datetime] = dict(data)
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode["exp"] = expire
    encoded_jwt: str = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    Dépendance pour extraire et valider l'utilisateur courant depuis le token JWT.

    Args:
        token: Token JWT extrait du header Authorization

    Returns:
        L'utilisateur authentifié

    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur n'existe pas
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    if token_data.username is None:
        raise credentials_exception

    user = user_service.get_user_by_username(username=token_data.username)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest) -> UserResponse:
    """
    Crée un nouveau compte utilisateur.

    Args:
        request: Données d'inscription (username, password)

    Returns:
        Informations de l'utilisateur créé (id, username)

    Raises:
        HTTPException: Si le nom d'utilisateur existe déjà (400)
    """
    try:
        user = user_service.create_user(
            username=request.username,
            password=request.password,
        )
        logger.info(f"New user registered: {user.username}")
        return UserResponse(id=user.id, username=user.username)
    except ValueError as e:
        logger.warning(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest) -> TokenResponse:
    """
    Authentifie un utilisateur et génère un token JWT.

    Args:
        request: Identifiants de connexion (username, password)

    Returns:
        Token JWT d'accès

    Raises:
        HTTPException: Si les identifiants sont incorrects (401)
    """
    user = user_service.authenticate_user(
        username=request.username,
        password=request.password,
    )

    if user is None:
        logger.warning(f"Failed login attempt for username: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Créer le token d'accès
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )

    logger.info(f"User logged in: {user.username}")
    return TokenResponse(access_token=access_token, token_type="bearer")
