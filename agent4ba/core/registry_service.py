"""Service de gestion du registre des agents et du mapping des intentions.

Ce module fournit des modèles Pydantic pour valider la configuration
des agents et des intentions, ainsi qu'une fonction de chargement
qui supporte la surcharge de configuration via un fichier local.
"""

import copy
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


class AgentConfig(BaseModel):
    """Configuration d'un agent.

    Attributes:
        id: Identifiant unique de l'agent (ex: "backlog_agent")
        description: Description des capacités et du rôle de l'agent
    """

    id: str = Field(..., description="Identifiant unique de l'agent")
    description: str = Field(..., description="Description des capacités de l'agent")


class IntentMapping(BaseModel):
    """Mapping entre une intention utilisateur et une tâche d'agent.

    Attributes:
        intent_id: Identifiant unique de l'intention (ex: "decompose_objective")
        agent_id: Identifiant de l'agent qui gère cette intention
        agent_task: Tâche interne exécutée par l'agent
        prompt_file: Chemin vers le fichier YAML contenant les prompts
        status: Statut optionnel (ex: "not_implemented" pour les stubs)
        description: Description optionnelle de l'intention
    """

    intent_id: str = Field(..., description="Identifiant unique de l'intention")
    agent_id: str = Field(..., description="Identifiant de l'agent responsable")
    agent_task: str = Field(..., description="Tâche interne de l'agent")
    prompt_file: str = Field(..., description="Chemin vers le fichier de prompts")
    status: str | None = Field(
        None, description="Statut optionnel (ex: not_implemented)"
    )
    description: str | None = Field(
        None, description="Description optionnelle de l'intention"
    )


class AgentRegistry(BaseModel):
    """Registre complet des agents et du mapping des intentions.

    Attributes:
        agents: Liste des agents disponibles
        intent_mapping: Liste des mappings intention -> tâche d'agent
    """

    agents: list[AgentConfig] = Field(..., description="Liste des agents disponibles")
    intent_mapping: list[IntentMapping] = Field(
        ..., description="Mapping des intentions vers les tâches"
    )

    def get_agent_by_id(self, agent_id: str) -> AgentConfig | None:
        """Récupère un agent par son identifiant.

        Args:
            agent_id: Identifiant de l'agent à rechercher

        Returns:
            L'AgentConfig correspondant ou None si non trouvé
        """
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None

    def get_intent_mapping(self, intent_id: str) -> IntentMapping | None:
        """Récupère le mapping d'une intention par son identifiant.

        Args:
            intent_id: Identifiant de l'intention à rechercher

        Returns:
            L'IntentMapping correspondant ou None si non trouvé
        """
        for mapping in self.intent_mapping:
            if mapping.intent_id == intent_id:
                return mapping
        return None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Fusionne récursivement deux dictionnaires.

    Les valeurs de `override` écrasent celles de `base`. Pour les listes,
    on effectue un remplacement complet (pas de fusion élément par élément).

    Args:
        base: Dictionnaire de base
        override: Dictionnaire de surcharge

    Returns:
        Nouveau dictionnaire fusionné
    """
    result = copy.deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Fusion récursive pour les dictionnaires
            result[key] = _deep_merge(result[key], value)
        else:
            # Remplacement direct pour les autres types (y compris les listes)
            result[key] = copy.deepcopy(value)

    return result


def load_agent_registry() -> AgentRegistry:
    """Charge et valide la configuration du registre des agents.

    Cette fonction implémente une logique de surcharge en deux étapes :
    1. Charge le fichier agent_registry.default.yaml (obligatoire)
    2. Tente de charger agent_registry.local.yaml (optionnel)
    3. Si le fichier local existe, fusionne sa configuration par-dessus
       celle par défaut (deep merge)
    4. Valide la configuration finale avec Pydantic

    Le fichier local permet de surcharger des valeurs spécifiques sans
    modifier le fichier par défaut versionné.

    Returns:
        Instance validée d'AgentRegistry contenant les agents et le mapping

    Raises:
        FileNotFoundError: Si le fichier par défaut n'existe pas
        ValidationError: Si la configuration ne respecte pas le schéma Pydantic
        yaml.YAMLError: Si les fichiers YAML sont mal formés
    """
    # Déterminer le chemin racine du projet (où se trouvent les fichiers YAML)
    # On remonte de agent4ba/core/ vers la racine
    project_root = Path(__file__).parent.parent.parent

    default_config_path = project_root / "agent_registry.default.yaml"
    local_config_path = project_root / "agent_registry.local.yaml"

    # 1. Charger le fichier par défaut (obligatoire)
    if not default_config_path.exists():
        raise FileNotFoundError(
            f"Le fichier de configuration par défaut est introuvable : {default_config_path}"
        )

    with default_config_path.open("r", encoding="utf-8") as f:
        default_data = yaml.safe_load(f)

    if not isinstance(default_data, dict):
        raise ValueError(
            f"Le fichier {default_config_path} ne contient pas un dictionnaire YAML valide"
        )

    # 2. Tenter de charger le fichier local (optionnel)
    final_data = default_data

    if local_config_path.exists():
        print(f"[REGISTRY_SERVICE] Chargement de la configuration locale : {local_config_path}")

        with local_config_path.open("r", encoding="utf-8") as f:
            local_data = yaml.safe_load(f)

        if not isinstance(local_data, dict):
            raise ValueError(
                f"Le fichier {local_config_path} ne contient pas un dictionnaire YAML valide"
            )

        # 3. Fusionner les configurations
        final_data = _deep_merge(default_data, local_data)
        print("[REGISTRY_SERVICE] Configuration locale fusionnée avec succès")
    else:
        print("[REGISTRY_SERVICE] Aucun fichier de configuration locale trouvé, "
              "utilisation de la configuration par défaut")

    # 4. Valider avec Pydantic
    try:
        registry = AgentRegistry(**final_data)
        print(f"[REGISTRY_SERVICE] Configuration validée : {len(registry.agents)} agents, "
              f"{len(registry.intent_mapping)} intentions")
        return registry
    except ValidationError as e:
        print(f"[REGISTRY_SERVICE] Erreur de validation de la configuration : {e}")
        raise


# Instance globale du registre (lazy loading)
_registry_instance: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Récupère l'instance globale du registre des agents.

    Cette fonction utilise un pattern singleton pour éviter de recharger
    la configuration à chaque appel. La configuration est chargée une seule
    fois lors du premier appel.

    Returns:
        Instance validée d'AgentRegistry

    Raises:
        FileNotFoundError: Si le fichier par défaut n'existe pas
        ValidationError: Si la configuration ne respecte pas le schéma Pydantic
    """
    global _registry_instance

    if _registry_instance is None:
        _registry_instance = load_agent_registry()

    return _registry_instance


def reset_agent_registry() -> None:
    """Réinitialise l'instance globale du registre.

    Utile pour les tests ou pour forcer le rechargement de la configuration.
    """
    global _registry_instance
    _registry_instance = None
