"""Models package for Agent4BA.

Ce package contient les modèles de données pour le projet,
notamment les modèles de schéma pour le backlog méta-modélisable.
"""

from agent4ba.models.schema import (
    FieldDefinition,
    ProjectSchema,
    WorkItemTypeDefinition,
)

__all__ = [
    "FieldDefinition",
    "WorkItemTypeDefinition",
    "ProjectSchema",
]
