"""Pydantic schemas for AI workflow components."""

from typing import Any

from pydantic import BaseModel, Field


class RouterDecision(BaseModel):
    """
    Schéma de décision du routeur avec Chain of Thought.

    Permet au LLM d'expliciter son raisonnement avant de prendre une décision
    de routage, rendant le processus plus transparent et auditable.
    """

    thought: str = Field(
        ...,
        description="Chaîne de pensée explicitant le raisonnement du LLM (analyse sémantique, extraction d'entités, justification)",
        min_length=10,
    )

    decision: dict[str, Any] = Field(
        ...,
        description="Décision de routage contenant 'agent', 'task', et 'args'",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "thought": "1. Analyse Sémantique: L'utilisateur souhaite créer un backlog complet pour un projet e-commerce. 2. Extraction d'Entités: Aucun ID de work item n'est mentionné, il s'agit d'une création from scratch. 3. Justification: epic_architect_agent est le spécialiste pour générer une liste exhaustive de features de haut niveau. 4. Décision: Utiliser epic_architect_agent avec la tâche generate_epics.",
                    "decision": {
                        "agent": "epic_architect_agent",
                        "task": "generate_epics",
                        "args": {
                            "objective": "site e-commerce de chaussures de luxe"
                        }
                    }
                },
                {
                    "thought": "1. Analyse Sémantique: L'utilisateur demande de décomposer une feature EXISTANTE. 2. Extraction d'Entités: ID 'FIR-3' détecté. 3. Justification: story_teller_agent est spécialisé dans la décomposition de features existantes en user stories. 4. Décision: Utiliser story_teller_agent avec decompose_feature_into_stories.",
                    "decision": {
                        "agent": "story_teller_agent",
                        "task": "decompose_feature_into_stories",
                        "args": {
                            "feature_id": "FIR-3"
                        }
                    }
                },
                {
                    "thought": "1. Analyse Sémantique: La requête concerne la météo, ce qui est hors-scope du système. 2. Extraction d'Entités: Aucun ID ou concept lié au backlog. 3. Justification: Aucun agent n'est adapté pour cette requête. 4. Décision: Utiliser fallback_agent pour informer l'utilisateur que la requête est hors-scope.",
                    "decision": {
                        "agent": "fallback_agent",
                        "task": "handle_unknown_intent",
                        "args": {}
                    }
                }
            ]
        }
    }

    def validate_decision(self) -> None:
        """
        Valide que la structure de 'decision' contient les clés requises.

        Raises:
            ValueError: Si la structure de 'decision' est invalide
        """
        required_keys = {"agent", "task", "args"}
        missing_keys = required_keys - set(self.decision.keys())

        if missing_keys:
            raise ValueError(
                f"Decision invalide: clés manquantes {missing_keys}. "
                f"Clés requises: {required_keys}"
            )

        # Vérifier que 'args' est bien un dict
        if not isinstance(self.decision["args"], dict):
            raise ValueError(
                f"Decision invalide: 'args' doit être un dict, pas {type(self.decision['args'])}"
            )
