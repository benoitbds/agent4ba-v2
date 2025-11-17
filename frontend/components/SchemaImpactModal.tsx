"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { ProjectSchema } from "@/types/events";
import { diffLines, Change } from "diff";

interface SchemaImpactModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApprove: () => void;
  oldSchema: ProjectSchema;
  newSchema: ProjectSchema;
  threadId: string;
}

/**
 * Composant pour afficher une ligne de diff avec sa couleur
 */
function DiffLine({ change }: { change: Change }) {
  const bgColor = change.added
    ? "bg-green-50"
    : change.removed
    ? "bg-red-50"
    : "bg-gray-50";
  const textColor = change.added
    ? "text-green-900"
    : change.removed
    ? "text-red-900"
    : "text-gray-700";
  const prefix = change.added ? "+ " : change.removed ? "- " : "  ";

  return (
    <div className={`${bgColor} ${textColor} px-3 py-1 font-mono text-sm border-b border-gray-200`}>
      <span className="select-none mr-2 font-bold">
        {prefix}
      </span>
      {change.value.split('\n').map((line, idx) => (
        line && <div key={idx} className="inline">{line}</div>
      ))}
    </div>
  );
}

export default function SchemaImpactModal({
  isOpen,
  onClose,
  onApprove,
  oldSchema,
  newSchema,
  threadId,
}: SchemaImpactModalProps) {
  const t = useTranslations();
  const [isProcessing, setIsProcessing] = useState(false);

  if (!isOpen) return null;

  const handleApprove = async () => {
    setIsProcessing(true);
    try {
      await onApprove();
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = () => {
    onClose();
  };

  // Convertir les schémas en JSON formaté
  const oldSchemaJson = JSON.stringify(oldSchema, null, 2);
  const newSchemaJson = JSON.stringify(newSchema, null, 2);

  // Calculer les différences
  const diff = diffLines(oldSchemaJson, newSchemaJson);

  // Compter les additions et suppressions
  const addedLines = diff.filter((change) => change.added).length;
  const removedLines = diff.filter((change) => change.removed).length;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">
            {t("schemaApproval.title") || "Proposition de modification du schéma"}
          </h2>
          <p className="text-sm text-gray-600 mt-1 font-mono">
            {t("schemaApproval.thread") || "Thread:"} {threadId}
          </p>
        </div>

        {/* Summary */}
        <div className="px-6 py-3 bg-blue-50 border-b border-blue-200">
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-green-700 font-semibold">
                +{addedLines}
              </span>
              <span className="text-gray-600">
                {t("schemaApproval.additions") || "ajouts"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-red-700 font-semibold">
                -{removedLines}
              </span>
              <span className="text-gray-600">
                {t("schemaApproval.deletions") || "suppressions"}
              </span>
            </div>
          </div>
        </div>

        {/* Content - Diff View */}
        <div className="flex-1 overflow-y-auto">
          <div className="divide-y divide-gray-200">
            {diff.map((change, index) => (
              <DiffLine key={index} change={change} />
            ))}
          </div>
        </div>

        {/* Info Box */}
        <div className="px-6 py-3 bg-yellow-50 border-t border-yellow-200">
          <div className="flex items-start gap-2">
            <span className="text-yellow-600 text-xl">⚠️</span>
            <div className="flex-1">
              <p className="text-sm text-yellow-900 font-semibold">
                {t("schemaApproval.warning") || "Attention"}
              </p>
              <p className="text-sm text-yellow-800 mt-1">
                {t("schemaApproval.warningMessage") ||
                  "Cette modification du schéma affectera la structure des WorkItems dans votre projet. Vérifiez attentivement les changements avant d'approuver."}
              </p>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={handleReject}
            disabled={isProcessing}
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {t("schemaApproval.reject") || "Rejeter"}
          </button>
          <button
            onClick={handleApprove}
            disabled={isProcessing}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isProcessing
              ? t("schemaApproval.processing") || "En cours..."
              : t("schemaApproval.approve") || "Approuver"}
          </button>
        </div>
      </div>
    </div>
  );
}
