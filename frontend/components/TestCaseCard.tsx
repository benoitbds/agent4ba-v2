"use client";

import { TestTube, ClipboardPlus, UserCheck, Sparkles } from "lucide-react";
import type { WorkItem } from "@/types/events";
import { useTranslations } from "next-intl";

interface TestCaseCardProps {
  testCase: WorkItem;
  onEdit?: (testCase: WorkItem) => void;
  onSelect?: (testCase: WorkItem) => void;
}

export default function TestCaseCard({ testCase, onEdit, onSelect }: TestCaseCardProps) {
  const t = useTranslations();

  return (
    <div
      onClick={() => onEdit?.(testCase)}
      className="ml-8 p-3 bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg border border-indigo-200 hover:border-indigo-400 transition-colors cursor-pointer shadow-sm"
    >
      <div className="flex items-start gap-2">
        {/* Icône distinctive pour les cas de test */}
        <div className="flex-shrink-0 mt-0.5">
          <TestTube className="w-4 h-4 text-indigo-600" />
        </div>

        {/* Tag Cas de Test */}
        <span className="px-2 py-0.5 text-xs font-semibold rounded bg-indigo-200 text-indigo-800 flex-shrink-0">
          {t("backlog.testCase")}
        </span>

        {/* Contenu du cas de test */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-sm font-semibold text-gray-800">
              {testCase.title}
            </h4>
            <span className="text-xs text-gray-500 font-mono">
              {testCase.id}
            </span>

            {/* Badge de statut de validation */}
            {testCase.validation_status === "human_validated" && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-semibold rounded bg-green-100 text-green-800 border border-green-300">
                <UserCheck className="w-2.5 h-2.5" />
                Validé
              </span>
            )}
            {testCase.validation_status === "ia_generated" && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-semibold rounded bg-amber-100 text-amber-800 border border-amber-300">
                <Sparkles className="w-2.5 h-2.5" />
                IA
              </span>
            )}
            {testCase.validation_status === "ia_modified" && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-semibold rounded bg-amber-100 text-amber-800 border border-amber-300">
                <Sparkles className="w-2.5 h-2.5" />
                IA (Modifié)
              </span>
            )}
          </div>

          {testCase.description && (
            <p className="text-xs text-gray-600 mt-1">
              {testCase.description}
            </p>
          )}
        </div>

        {/* Bouton d'action pour ajouter au contexte */}
        {onSelect && (
          <div className="flex-shrink-0">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSelect(testCase);
              }}
              className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-green-500"
              title={t("backlog.addToContext")}
            >
              <ClipboardPlus className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
