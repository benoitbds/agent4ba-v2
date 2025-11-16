/**
 * Utilitaires pour calculer les différences entre deux WorkItems
 */

import type { WorkItem, Diagram } from "@/types/events";

/**
 * Type représentant un changement simple d'une valeur
 */
export interface SimpleChange<T> {
  from: T;
  to: T;
}

/**
 * Type représentant un changement dans un tableau
 */
export interface ArrayChange<T> {
  added: T[];
  removed: T[];
  unchanged: T[];
}

/**
 * Type représentant un changement de diagramme
 */
export interface DiagramChange {
  added: Diagram[];
  removed: Diagram[];
  modified: Array<{ before: Diagram; after: Diagram }>;
  unchanged: Diagram[];
}

/**
 * Type représentant tous les changements possibles dans un WorkItem
 */
export interface WorkItemDiff {
  title: SimpleChange<string> | null;
  description: SimpleChange<string> | null;
  acceptance_criteria: ArrayChange<string> | null;
  diagrams: DiagramChange | null;
  type: SimpleChange<WorkItem["type"]> | null;
  parent_id: SimpleChange<string | null> | null;
  validation_status: SimpleChange<WorkItem["validation_status"]> | null;
  attributes: {
    priority: SimpleChange<string | undefined> | null;
    status: SimpleChange<string | undefined> | null;
    points: SimpleChange<number | undefined> | null;
    [key: string]: SimpleChange<unknown> | null;
  };
}

/**
 * Compare deux valeurs simples et retourne un objet de changement si différentes
 */
function compareSimpleValue<T>(before: T, after: T): SimpleChange<T> | null {
  if (before === after) {
    return null;
  }
  return { from: before, to: after };
}

/**
 * Compare deux tableaux et retourne les éléments ajoutés, supprimés et inchangés
 */
function compareArrays<T>(
  before: T[] = [],
  after: T[] = []
): ArrayChange<T> | null {
  const beforeSet = new Set(before);
  const afterSet = new Set(after);

  const added = after.filter((item) => !beforeSet.has(item));
  const removed = before.filter((item) => !afterSet.has(item));
  const unchanged = after.filter((item) => beforeSet.has(item));

  // S'il n'y a aucun changement, retourner null
  if (added.length === 0 && removed.length === 0) {
    return null;
  }

  return { added, removed, unchanged };
}

/**
 * Compare deux tableaux de diagrammes
 */
function compareDiagrams(
  before: Diagram[] = [],
  after: Diagram[] = []
): DiagramChange | null {
  const beforeMap = new Map(before.map((d) => [d.id, d]));
  const afterMap = new Map(after.map((d) => [d.id, d]));

  const added: Diagram[] = [];
  const removed: Diagram[] = [];
  const modified: Array<{ before: Diagram; after: Diagram }> = [];
  const unchanged: Diagram[] = [];

  // Trouver les diagrammes ajoutés, modifiés et inchangés
  for (const afterDiagram of after) {
    const beforeDiagram = beforeMap.get(afterDiagram.id);

    if (!beforeDiagram) {
      // Nouveau diagramme
      added.push(afterDiagram);
    } else {
      // Vérifier si le diagramme a été modifié
      const hasChanged =
        beforeDiagram.title !== afterDiagram.title ||
        beforeDiagram.code !== afterDiagram.code;

      if (hasChanged) {
        modified.push({ before: beforeDiagram, after: afterDiagram });
      } else {
        unchanged.push(afterDiagram);
      }
    }
  }

  // Trouver les diagrammes supprimés
  for (const diagram of before) {
    if (!afterMap.has(diagram.id)) {
      removed.push(diagram);
    }
  }

  // S'il n'y a aucun changement, retourner null
  if (added.length === 0 && removed.length === 0 && modified.length === 0) {
    return null;
  }

  return { added, removed, modified, unchanged };
}

/**
 * Compare les attributs de deux WorkItems
 */
function compareAttributes(
  before: WorkItem["attributes"],
  after: WorkItem["attributes"]
): WorkItemDiff["attributes"] {
  const result: WorkItemDiff["attributes"] = {
    priority: compareSimpleValue(before.priority, after.priority),
    status: compareSimpleValue(before.status, after.status),
    points: compareSimpleValue(before.points, after.points),
  };

  // Comparer les attributs personnalisés
  const allKeys = new Set([
    ...Object.keys(before),
    ...Object.keys(after),
  ]);

  for (const key of allKeys) {
    if (key !== "priority" && key !== "status" && key !== "points") {
      const change = compareSimpleValue(before[key], after[key]);
      if (change !== null) {
        result[key] = change;
      }
    }
  }

  return result;
}

/**
 * Calcule les différences entre deux WorkItems
 * @param before L'état précédent du WorkItem
 * @param after L'état actuel du WorkItem
 * @returns Un objet contenant toutes les différences détectées
 */
export function calculateDiff(before: WorkItem, after: WorkItem): WorkItemDiff {
  return {
    title: compareSimpleValue(before.title, after.title),
    description: compareSimpleValue(before.description, after.description),
    acceptance_criteria: compareArrays(
      before.acceptance_criteria,
      after.acceptance_criteria
    ),
    diagrams: compareDiagrams(before.diagrams, after.diagrams),
    type: compareSimpleValue(before.type, after.type),
    parent_id: compareSimpleValue(before.parent_id, after.parent_id),
    validation_status: compareSimpleValue(
      before.validation_status,
      after.validation_status
    ),
    attributes: compareAttributes(before.attributes, after.attributes),
  };
}

/**
 * Vérifie si un diff contient des changements
 */
export function hasDiff(diff: WorkItemDiff): boolean {
  return (
    diff.title !== null ||
    diff.description !== null ||
    diff.acceptance_criteria !== null ||
    diff.diagrams !== null ||
    diff.type !== null ||
    diff.parent_id !== null ||
    diff.validation_status !== null ||
    Object.values(diff.attributes).some((attr) => attr !== null)
  );
}
