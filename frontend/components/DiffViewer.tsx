"use client";

import { useTranslations } from "next-intl";
import type { WorkItem } from "@/types/events";
import { calculateDiff, hasDiff, type WorkItemDiff, type SimpleChange, type ArrayChange, type DiagramChange } from "@/lib/diff";
import { type ReactElement } from "react";

interface DiffViewerProps {
  before: WorkItem;
  after: WorkItem;
}

/**
 * Composant pour afficher un changement simple (texte)
 */
function SimpleChangeDiff({
  label,
  change,
}: {
  label: string;
  change: SimpleChange<string | number | boolean | null>;
}): ReactElement {
  return (
    <div className="border border-gray-300 rounded overflow-hidden mb-3">
      <div className="bg-gray-100 px-3 py-2 border-b border-gray-300">
        <span className="text-sm font-semibold text-gray-700">{label}</span>
      </div>
      <div className="grid grid-cols-2 divide-x divide-gray-300">
        {/* Before (left side) */}
        <div className="bg-red-50">
          <div className="bg-red-100 px-3 py-1 border-b border-red-200">
            <span className="text-xs font-semibold text-red-800">Avant</span>
          </div>
          <div className="p-3 text-sm text-gray-800 whitespace-pre-wrap">
            <span className="line-through">{String(change.from || "")}</span>
          </div>
        </div>
        {/* After (right side) */}
        <div className="bg-green-50">
          <div className="bg-green-100 px-3 py-1 border-b border-green-200">
            <span className="text-xs font-semibold text-green-800">Après</span>
          </div>
          <div className="p-3 text-sm text-gray-800 whitespace-pre-wrap">
            <span className="font-semibold">{String(change.to || "")}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Composant pour afficher un changement dans une liste (acceptance criteria)
 */
function ArrayChangeDiff({
  label,
  change,
}: {
  label: string;
  change: ArrayChange<string>;
}): ReactElement {
  return (
    <div className="border border-gray-300 rounded overflow-hidden mb-3">
      <div className="bg-gray-100 px-3 py-2 border-b border-gray-300">
        <span className="text-sm font-semibold text-gray-700">{label}</span>
      </div>
      <div className="p-3 space-y-2">
        {/* Éléments supprimés */}
        {change.removed.map((item, index) => (
          <div
            key={`removed-${index}`}
            className="flex items-start gap-2 p-2 bg-red-50 border border-red-200 rounded"
          >
            <span className="text-red-600 font-bold text-sm flex-shrink-0">−</span>
            <span className="text-sm text-red-800 line-through">{item}</span>
          </div>
        ))}
        {/* Éléments ajoutés */}
        {change.added.map((item, index) => (
          <div
            key={`added-${index}`}
            className="flex items-start gap-2 p-2 bg-green-50 border border-green-200 rounded"
          >
            <span className="text-green-600 font-bold text-sm flex-shrink-0">+</span>
            <span className="text-sm text-green-800 font-semibold">{item}</span>
          </div>
        ))}
        {/* Éléments inchangés (affichés en gris léger) */}
        {change.unchanged.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <span className="text-xs text-gray-500 font-semibold block mb-2">
              Inchangés ({change.unchanged.length})
            </span>
            {change.unchanged.map((item, index) => (
              <div
                key={`unchanged-${index}`}
                className="flex items-start gap-2 p-2 bg-gray-50 border border-gray-200 rounded mb-1"
              >
                <span className="text-gray-400 text-sm flex-shrink-0">•</span>
                <span className="text-sm text-gray-600">{item}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Composant pour afficher les changements de diagrammes
 */
function DiagramChangeDiff({
  change,
}: {
  change: DiagramChange;
}): ReactElement {
  const t = useTranslations();

  return (
    <div className="border border-blue-300 rounded overflow-hidden mb-3">
      <div className="bg-blue-100 px-3 py-2 border-b border-blue-200">
        <span className="text-sm font-semibold text-blue-800">
          {t("backlog.diagrams")}
        </span>
      </div>
      <div className="p-3 space-y-2">
        {/* Diagrammes supprimés */}
        {change.removed.map((diagram) => (
          <div
            key={`removed-${diagram.id}`}
            className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded"
          >
            <span className="text-red-600 font-bold text-sm flex-shrink-0">−</span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-red-800 line-through">
                  {diagram.title}
                </span>
                <span className="text-xs text-red-600 font-mono">
                  {diagram.id}
                </span>
              </div>
              <div className="text-xs text-red-700">
                Diagramme supprimé
              </div>
            </div>
          </div>
        ))}

        {/* Diagrammes ajoutés */}
        {change.added.map((diagram) => (
          <div
            key={`added-${diagram.id}`}
            className="flex items-start gap-2 p-3 bg-green-50 border border-green-200 rounded"
          >
            <span className="text-green-600 font-bold text-sm flex-shrink-0">+</span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-green-800">
                  ✨ {diagram.title}
                </span>
                <span className="text-xs text-green-600 font-mono">
                  {diagram.id}
                </span>
              </div>
              <div className="text-xs text-green-700">
                {t("timeline.diagramAdded")}
              </div>
            </div>
          </div>
        ))}

        {/* Diagrammes modifiés */}
        {change.modified.map(({ before, after }) => (
          <div
            key={`modified-${after.id}`}
            className="border border-orange-200 rounded overflow-hidden bg-orange-50"
          >
            <div className="bg-orange-100 px-3 py-2 border-b border-orange-200">
              <span className="text-sm font-semibold text-orange-800">
                ✏️ Diagramme modifié
              </span>
            </div>
            <div className="grid grid-cols-2 divide-x divide-orange-200">
              {/* Before */}
              <div className="p-3 bg-red-50">
                <div className="text-xs font-semibold text-red-800 mb-2">Avant</div>
                <div className="text-sm text-gray-800">
                  <div className="font-semibold line-through">{before.title}</div>
                  <div className="text-xs text-gray-600 font-mono mt-1">{before.id}</div>
                </div>
              </div>
              {/* After */}
              <div className="p-3 bg-green-50">
                <div className="text-xs font-semibold text-green-800 mb-2">Après</div>
                <div className="text-sm text-gray-800">
                  <div className="font-semibold">{after.title}</div>
                  <div className="text-xs text-gray-600 font-mono mt-1">{after.id}</div>
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Diagrammes inchangés */}
        {change.unchanged.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <span className="text-xs text-gray-500 font-semibold block mb-2">
              Inchangés ({change.unchanged.length})
            </span>
            {change.unchanged.map((diagram) => (
              <div
                key={`unchanged-${diagram.id}`}
                className="flex items-start gap-2 p-2 bg-gray-50 border border-gray-200 rounded mb-1"
              >
                <span className="text-gray-400 text-sm flex-shrink-0">•</span>
                <div className="flex-1">
                  <span className="text-sm text-gray-600">{diagram.title}</span>
                  <span className="text-xs text-gray-500 font-mono ml-2">{diagram.id}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Composant pour afficher les changements d'attributs
 */
function AttributesDiff({
  diff,
}: {
  diff: WorkItemDiff["attributes"];
}): ReactElement | null {
  const t = useTranslations();

  const hasChanges = Object.values(diff).some((attr) => attr !== null);

  if (!hasChanges) {
    return null;
  }

  return (
    <div className="border border-gray-300 rounded overflow-hidden mb-3">
      <div className="bg-gray-100 px-3 py-2 border-b border-gray-300">
        <span className="text-sm font-semibold text-gray-700">
          {t("backlog.attributes")}
        </span>
      </div>
      <div className="p-3 space-y-2">
        {diff.priority && (
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-gray-700">{t("backlog.priority")}:</span>
            <span className="px-2 py-1 bg-red-100 text-red-800 rounded line-through">
              {String(diff.priority.from)}
            </span>
            <span className="text-gray-400">→</span>
            <span className="px-2 py-1 bg-green-100 text-green-800 rounded font-semibold">
              {String(diff.priority.to)}
            </span>
          </div>
        )}
        {diff.status && (
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-gray-700">{t("backlog.status")}:</span>
            <span className="px-2 py-1 bg-red-100 text-red-800 rounded line-through">
              {String(diff.status.from)}
            </span>
            <span className="text-gray-400">→</span>
            <span className="px-2 py-1 bg-green-100 text-green-800 rounded font-semibold">
              {String(diff.status.to)}
            </span>
          </div>
        )}
        {diff.points && (
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-gray-700">{t("backlog.points")}:</span>
            <span className="px-2 py-1 bg-red-100 text-red-800 rounded line-through">
              {String(diff.points.from)}
            </span>
            <span className="text-gray-400">→</span>
            <span className="px-2 py-1 bg-green-100 text-green-800 rounded font-semibold">
              {String(diff.points.to)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Composant principal DiffViewer
 * Affiche les différences entre deux versions d'un WorkItem
 */
export default function DiffViewer({ before, after }: DiffViewerProps): ReactElement {
  const t = useTranslations();
  const diff = calculateDiff(before, after);

  // Si aucun changement détecté, afficher un message
  if (!hasDiff(diff)) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-sm text-gray-600 italic">{t("timeline.noChanges")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Changement de titre */}
      {diff.title && (
        <SimpleChangeDiff label={t("backlog.title")} change={diff.title} />
      )}

      {/* Changement de description */}
      {diff.description && (
        <SimpleChangeDiff
          label={t("backlog.description")}
          change={diff.description}
        />
      )}

      {/* Changement de type */}
      {diff.type && (
        <SimpleChangeDiff label={t("backlog.type")} change={diff.type} />
      )}

      {/* Changement de critères d'acceptation */}
      {diff.acceptance_criteria && (
        <ArrayChangeDiff
          label={t("backlog.acceptanceCriteria")}
          change={diff.acceptance_criteria}
        />
      )}

      {/* Changements de diagrammes */}
      {diff.diagrams && (
        <DiagramChangeDiff change={diff.diagrams} />
      )}

      {/* Changements d'attributs */}
      <AttributesDiff diff={diff.attributes} />
    </div>
  );
}
