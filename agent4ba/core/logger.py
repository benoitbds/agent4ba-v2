"""Module de configuration centralisée du logging pour Agent4BA V2.

Ce module fournit une fonction utilitaire pour créer et configurer
des instances de logger avec un format standardisé et cohérent dans
toute l'application.
"""

import logging
import os
import sys


def setup_logger(name: str) -> logging.Logger:
    """Configure et retourne une instance de logger avec un format standardisé.

    Cette fonction crée un logger avec un handler sur stdout et un format
    unifié pour tous les messages de log. Elle évite d'ajouter plusieurs
    handlers au même logger en cas d'appels multiples.

    Le niveau de log peut être configuré via la variable d'environnement LOG_LEVEL.
    Par défaut, le niveau est DEBUG pour faciliter le diagnostic.

    Args:
        name: Le nom du logger, généralement le nom du module (__name__).

    Returns:
        Une instance configurée de logging.Logger prête à l'emploi.

    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Application démarrée")
        2025-11-13 12:00:00,000 - mymodule - INFO - Application démarrée
    """
    logger = logging.getLogger(name)

    # Éviter d'ajouter des handlers multiples si le logger en a déjà
    if not logger.handlers:
        # Lire le niveau de log depuis la variable d'environnement
        log_level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
        log_level = getattr(logging, log_level_str, logging.DEBUG)

        logger.setLevel(log_level)

        # Créer un handler pour écrire sur stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        # Définir le format des messages de log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # Ajouter le handler au logger
        logger.addHandler(handler)

    return logger
