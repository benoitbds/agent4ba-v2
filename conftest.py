"""Configuration pytest globale pour tous les tests."""

import pytest

from agent4ba.core.registry_service import load_agent_registry, reset_agent_registry


@pytest.fixture(scope="module")
def graph():
    """
    Fixture qui charge le graph LangGraph pour les tests.

    Returns:
        Le module graph avec le workflow configuré
    """
    from agent4ba.ai import graph as graph_module

    return graph_module


@pytest.fixture(scope="module")
def registry():
    """
    Fixture qui charge le registre des agents pour les tests.

    Returns:
        Le registre des agents chargé
    """
    # Réinitialiser le cache pour chaque module de test
    reset_agent_registry()
    return load_agent_registry()


@pytest.fixture
def test_case(request):
    """
    Fixture paramétrée pour les cas de test d'intentions.

    Cette fixture permet d'exécuter le même test avec différents paramètres.
    """
    return request.param
