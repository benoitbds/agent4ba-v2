"""Utility functions for WorkItem ID management."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent4ba.core.models import WorkItem


def generate_project_prefix(project_id: str) -> str:
    """
    Génère un préfixe de projet à partir du project_id.

    Prend le premier mot du project_id (avant le premier tiret) et
    utilise les 3 premières lettres en majuscules.

    Exemples:
        - "recette-mvp" -> "REC"
        - "mon-projet-test" -> "MON"
        - "ab-test" -> "AB"
        - "project" -> "PRO"

    Args:
        project_id: L'identifiant du projet

    Returns:
        Le préfixe en majuscules (2 à 3 caractères)
    """
    # Prendre le premier mot (avant le premier tiret ou underscore)
    first_word = re.split(r'[-_]', project_id)[0]

    # Nettoyer les caractères non-alphabétiques
    clean_word = re.sub(r'[^a-zA-Z]', '', first_word)

    if not clean_word:
        # Si aucun caractère alphabétique, utiliser "PROJ" par défaut
        return "PROJ"

    # Prendre les 3 premières lettres (ou moins si le mot est court)
    prefix = clean_word[:3].upper()

    # S'assurer qu'on a au moins 2 caractères
    if len(prefix) < 2:
        prefix = prefix + "X" * (2 - len(prefix))

    return prefix


def get_next_sequential_index(
    project_id: str,
    existing_items: list["WorkItem"]
) -> tuple[str, int]:
    """
    Calcule le prochain index séquentiel disponible pour un projet.

    Scanne tous les WorkItems existants dans le backlog du projet,
    parse leurs ID pour trouver le plus grand numéro après le préfixe du projet.
    Si aucun item n'existe avec ce préfixe, l'index de départ est 1.

    Args:
        project_id: L'identifiant du projet
        existing_items: Liste des WorkItems existants dans le backlog

    Returns:
        Un tuple (prefix, next_index) où:
            - prefix: Le préfixe du projet (ex: "REC")
            - next_index: Le prochain index disponible (au moins 1)

    Examples:
        >>> get_next_sequential_index("recette-mvp", [])
        ("REC", 1)

        >>> items = [WorkItem(id="REC-1", ...), WorkItem(id="REC-3", ...)]
        >>> get_next_sequential_index("recette-mvp", items)
        ("REC", 4)
    """
    prefix = generate_project_prefix(project_id)
    max_index = 0

    # Pattern pour matcher les ID avec le préfixe du projet
    # Format attendu: PREFIX-NUMBER (ex: REC-1, MON-42)
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")

    for item in existing_items:
        match = pattern.match(item.id)
        if match:
            try:
                index = int(match.group(1))
                max_index = max(max_index, index)
            except (ValueError, IndexError):
                # Ignorer les ID mal formés
                continue

    return prefix, max_index + 1


def assign_sequential_ids(
    project_id: str,
    existing_items: list["WorkItem"],
    new_items_data: list[dict]
) -> list[dict]:
    """
    Assigne des ID séquentiels à une liste de nouveaux WorkItems.

    Cette fonction prend une liste de dictionnaires représentant de nouveaux
    WorkItems (typiquement générés par le LLM) et leur assigne des ID
    séquentiels uniques basés sur le préfixe du projet.

    IMPORTANT: Cette fonction met également à jour les parent_id pour maintenir
    la cohérence des relations hiérarchiques après le remplacement des IDs.

    Args:
        project_id: L'identifiant du projet
        existing_items: Liste des WorkItems existants dans le backlog
        new_items_data: Liste de dictionnaires représentant les nouveaux items

    Returns:
        La même liste de dictionnaires avec les ID et parent_id mis à jour

    Examples:
        >>> new_items = [
        ...     {"id": "temp-1", "title": "Feature 1", "parent_id": null, ...},
        ...     {"id": "temp-2", "title": "Story 1", "parent_id": "temp-1", ...}
        ... ]
        >>> assign_sequential_ids("recette-mvp", [], new_items)
        [
            {"id": "REC-1", "title": "Feature 1", "parent_id": null, ...},
            {"id": "REC-2", "title": "Story 1", "parent_id": "REC-1", ...}
        ]
    """
    prefix, start_index = get_next_sequential_index(project_id, existing_items)

    # Créer un mapping des anciens IDs vers les nouveaux IDs
    id_mapping = {}
    for i, item_data in enumerate(new_items_data):
        old_id = item_data["id"]
        new_id = f"{prefix}-{start_index + i}"
        id_mapping[old_id] = new_id

    # Première passe : remplacer les IDs
    for i, item_data in enumerate(new_items_data):
        item_data["id"] = f"{prefix}-{start_index + i}"

    # Deuxième passe : mettre à jour les parent_id en utilisant le mapping
    for item_data in new_items_data:
        parent_id = item_data.get("parent_id")
        if parent_id and parent_id in id_mapping:
            item_data["parent_id"] = id_mapping[parent_id]

    return new_items_data
