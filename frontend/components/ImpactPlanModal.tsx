"use client";

import { useTranslations } from "next-intl";
import type { ImpactPlan, WorkItem, ModifiedItem } from "@/types/events";
import { useState, type ReactElement } from "react";
import DiffViewer from "./DiffViewer";
import MermaidDiagram from "./MermaidDiagram";

interface ImpactPlanModalProps {
  impactPlan: ImpactPlan;
  threadId: string;
  onApprove: () => void;
  onReject: () => void;
  isOpen: boolean;
}

interface InvestCriterion {
  score: number;
  reason: string;
}

interface InvestAnalysis {
  I: InvestCriterion;
  N: InvestCriterion;
  V: InvestCriterion;
  E: InvestCriterion;
  S: InvestCriterion;
  T: InvestCriterion;
}

// Fonction pour déterminer la couleur du badge selon le score
function getBadgeColor(score: number): string {
  if (score > 0.8) return "bg-green-500 text-white";
  if (score > 0.6) return "bg-orange-500 text-white";
  return "bg-red-500 text-white";
}

// Composant pour afficher un item modifié avec diff visuel
function ModifiedItemView({ modifiedItem }: { modifiedItem: ModifiedItem }): ReactElement {
  const t = useTranslations();
  const { before, after } = modifiedItem;

  // Détecter si l'analyse INVEST a été ajoutée
  const hasInvestAnalysis = after.attributes?.invest_analysis && !before.attributes?.invest_analysis;
  const investAnalysis = after.attributes?.invest_analysis as InvestAnalysis | undefined;

  // Détecter si des diagrammes ont été ajoutés
  const beforeDiagrams = before.diagrams || [];
  const afterDiagrams = after.diagrams || [];
  const addedDiagrams = afterDiagrams.filter(
    (afterDiagram) => !beforeDiagrams.some((beforeDiagram) => beforeDiagram.id === afterDiagram.id)
  );

  return (
    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-start gap-2 mb-4">
        <span
          className={`px-2 py-1 text-xs font-semibold rounded ${
            before.type === "feature"
              ? "bg-purple-200 text-purple-800"
              : before.type === "story"
              ? "bg-blue-200 text-blue-800"
              : "bg-green-200 text-green-800"
          }`}
        >
          {before.type}
        </span>
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900">{before.title}</h4>
          <p className="text-xs text-gray-500">ID: {before.id}</p>
        </div>
      </div>

      {/* Utilisation du nouveau composant DiffViewer */}
      <DiffViewer before={before} after={after} />

      {/* Diagrammes ajoutés */}
      {addedDiagrams.length > 0 && (
        <div className="mt-3 border border-blue-300 rounded overflow-hidden bg-blue-50">
          <div className="bg-blue-100 px-3 py-2 border-b border-blue-200">
            <span className="text-sm font-semibold text-blue-800">
              ✨ {addedDiagrams.length === 1
                ? t("timeline.diagramAdded")
                : t("timeline.diagramsAdded", { count: addedDiagrams.length })}
            </span>
          </div>
          <div className="p-3 space-y-2">
            {addedDiagrams.map((diagram) => (
              <div key={diagram.id} className="bg-white p-3 rounded border border-blue-200">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-semibold text-blue-900">
                    {diagram.title}
                  </span>
                  <span className="text-xs text-blue-600 font-mono">
                    {diagram.id}
                  </span>
                </div>
                <div className="text-xs text-blue-700 mb-3">
                  {t("timeline.diagramAddedToItem", { itemId: after.id })}
                </div>
                {/* Prévisualisation du diagramme */}
                <div className="mt-2">
                  <MermaidDiagram code={diagram.code} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analyse INVEST ajoutée (conservée en plus du diff) */}
      {hasInvestAnalysis && investAnalysis ? (
        <div className="mt-3 border border-green-300 rounded overflow-hidden bg-green-50">
          <div className="bg-green-100 px-3 py-2 border-b border-green-200">
            <span className="text-sm font-semibold text-green-800">
              {t("timeline.investAnalysisAdded")}
            </span>
          </div>
          <div className="p-3">
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(investAnalysis).map(([criterion, data]) => (
                <div key={criterion} className="bg-white p-2 rounded border border-gray-200">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`px-2 py-1 text-xs font-bold rounded ${getBadgeColor(data.score)}`}
                    >
                      {criterion}
                    </span>
                    <span className="text-xs font-semibold text-gray-700">
                      {t(`invest.${criterion}`)}
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 mb-1">
                    {t("timeline.score")} {(data.score * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-700">
                    {data.reason}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function ImpactPlanModal({
  impactPlan,
  threadId,
  onApprove,
  onReject,
  isOpen,
}: ImpactPlanModalProps) {
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

  const handleReject = async () => {
    setIsProcessing(true);
    try {
      await onReject();
    } finally {
      setIsProcessing(false);
    }
  };

  const renderWorkItem = (item: WorkItem) => (
    <div
      key={item.id}
      className="p-4 bg-gray-50 rounded-lg border border-gray-200"
    >
      <div className="flex items-start gap-2">
        <span
          className={`px-2 py-1 text-xs font-semibold rounded ${
            item.type === "feature"
              ? "bg-purple-200 text-purple-800"
              : item.type === "story"
              ? "bg-blue-200 text-blue-800"
              : "bg-green-200 text-green-800"
          }`}
        >
          {item.type}
        </span>
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900">{item.title}</h4>
          <p className="text-sm text-gray-600 mt-1">{item.description}</p>
          {item.attributes && (
            <div className="flex gap-2 mt-2 text-xs">
              {item.attributes.priority && (
                <span className="px-2 py-1 bg-gray-200 rounded">
                  {t("backlog.priority")} {item.attributes.priority}
                </span>
              )}
              {item.attributes.points !== undefined && (
                <span className="px-2 py-1 bg-gray-200 rounded">
                  {t("backlog.points")} {item.attributes.points}
                </span>
              )}
              {item.attributes.status && (
                <span className="px-2 py-1 bg-gray-200 rounded">
                  {t("backlog.status")} {item.attributes.status}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">
            {t("impactPlan.title")}
          </h2>
          <p className="text-sm text-gray-600 mt-1 font-mono">
            {t("impactPlan.thread")} {threadId}
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* New Items */}
          {impactPlan.new_items.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <span className="text-green-600">✨</span>
                {t("timeline.newItems")} ({impactPlan.new_items.length})
              </h3>
              <div className="space-y-3">
                {impactPlan.new_items.map(renderWorkItem)}
              </div>
            </div>
          )}

          {/* Modified Items */}
          {impactPlan.modified_items.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <span className="text-blue-600">✏️</span>
                {t("timeline.modifiedItems")} ({impactPlan.modified_items.length})
              </h3>
              <div className="space-y-3">
                {impactPlan.modified_items.map((item) => (
                  <ModifiedItemView key={item.before.id} modifiedItem={item} />
                ))}
              </div>
            </div>
          )}

          {/* Deleted Items */}
          {impactPlan.deleted_items.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <span className="text-red-600">🗑️</span>
                {t("timeline.deletedItems")} ({impactPlan.deleted_items.length})
              </h3>
              <div className="space-y-2">
                {impactPlan.deleted_items.map((itemId) => (
                  <div
                    key={itemId}
                    className="p-3 bg-red-50 rounded-lg border border-red-200"
                  >
                    <p className="text-sm text-red-800 font-mono">{itemId}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Summary */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
            <h4 className="font-semibold text-blue-900 mb-2">{t("timeline.summary")}</h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>
                • {impactPlan.new_items.length} {impactPlan.new_items.length > 1 ? t("timeline.newItems_plural") : t("timeline.newItem")}
              </li>
              <li>
                • {impactPlan.modified_items.length} {impactPlan.modified_items.length > 1 ? t("timeline.modifiedItems_plural") : t("timeline.modifiedItem")}
              </li>
              <li>
                • {impactPlan.deleted_items.length} {impactPlan.deleted_items.length > 1 ? t("timeline.deletedItems_plural") : t("timeline.deletedItem")}
              </li>
            </ul>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={handleReject}
            disabled={isProcessing}
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {t("impactPlan.reject")}
          </button>
          <button
            onClick={handleApprove}
            disabled={isProcessing}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isProcessing ? t("impactPlan.processing") : t("impactPlan.approve")}
          </button>
        </div>
      </div>
    </div>
  );
}
