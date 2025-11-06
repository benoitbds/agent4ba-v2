"use client";

import type { ImpactPlan, WorkItem, ModifiedItem } from "@/types/events";
import { useState } from "react";

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

// Noms complets des critères INVEST
const INVEST_LABELS: Record<string, string> = {
  I: "Independent (Indépendante)",
  N: "Negotiable (Négociable)",
  V: "Valuable (Apporte de la valeur)",
  E: "Estimable (Estimable)",
  S: "Small (Petite)",
  T: "Testable (Testable)",
};

// Composant pour afficher un item modifié avec diff visuel simple
function ModifiedItemView({ modifiedItem }: { modifiedItem: ModifiedItem }) {
  const { before, after } = modifiedItem;

  // Détecter si l'analyse INVEST a été ajoutée
  const hasInvestAnalysis = after.attributes?.invest_analysis && !before.attributes?.invest_analysis;
  const investAnalysis = after.attributes?.invest_analysis as InvestAnalysis | undefined;

  // Détecter si la description a changé
  const descriptionChanged = before.description !== after.description;

  return (
    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-start gap-2 mb-4">
        <span
          className={`px-2 py-1 text-xs font-semibold rounded ${
            before.type === "feature"
              ? "bg-purple-200 text-purple-800"
              : before.type === "user_story"
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

      {/* Diff de description (uniquement si modifiée) */}
      {descriptionChanged && (
        <div className="mt-3 border border-gray-300 rounded overflow-hidden">
          <div className="bg-gray-100 px-3 py-2 border-b border-gray-300">
            <span className="text-sm font-semibold text-gray-700">
              Modifications de la description
            </span>
          </div>

          {/* Split view with before/after */}
          <div className="grid grid-cols-2 divide-x divide-gray-300">
            {/* Before (left side) */}
            <div className="bg-red-50">
              <div className="bg-red-100 px-3 py-1 border-b border-red-200">
                <span className="text-xs font-semibold text-red-800">Avant</span>
              </div>
              <div className="p-3 text-sm text-gray-800 whitespace-pre-wrap">
                {before.description || "(vide)"}
              </div>
            </div>

            {/* After (right side) */}
            <div className="bg-green-50">
              <div className="bg-green-100 px-3 py-1 border-b border-green-200">
                <span className="text-xs font-semibold text-green-800">Après</span>
              </div>
              <div className="p-3 text-sm text-gray-800 whitespace-pre-wrap">
                {after.description || "(vide)"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Analyse INVEST ajoutée */}
      {hasInvestAnalysis && investAnalysis && (
        <div className="mt-3 border border-green-300 rounded overflow-hidden bg-green-50">
          <div className="bg-green-100 px-3 py-2 border-b border-green-200">
            <span className="text-sm font-semibold text-green-800">
              ✅ Analyse INVEST ajoutée
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
                      {INVEST_LABELS[criterion]}
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 mb-1">
                    Score: {(data.score * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-700">
                    {data.reason}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Autres attributs */}
      {after.attributes && (
        <div className="flex gap-2 mt-3 text-xs">
          {after.attributes.priority && (
            <span className="px-2 py-1 bg-gray-200 rounded">
              Priorité: {after.attributes.priority}
            </span>
          )}
          {after.attributes.points !== undefined && (
            <span className="px-2 py-1 bg-gray-200 rounded">
              Points: {after.attributes.points}
            </span>
          )}
          {after.attributes.status && (
            <span className="px-2 py-1 bg-gray-200 rounded">
              Statut: {after.attributes.status}
            </span>
          )}
        </div>
      )}
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
              : item.type === "user_story"
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
                  Priorité: {item.attributes.priority}
                </span>
              )}
              {item.attributes.points !== undefined && (
                <span className="px-2 py-1 bg-gray-200 rounded">
                  Points: {item.attributes.points}
                </span>
              )}
              {item.attributes.status && (
                <span className="px-2 py-1 bg-gray-200 rounded">
                  Statut: {item.attributes.status}
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
            Validation de l&apos;ImpactPlan
          </h2>
          <p className="text-sm text-gray-600 mt-1 font-mono">
            Thread: {threadId}
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* New Items */}
          {impactPlan.new_items.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <span className="text-green-600">✨</span>
                Nouveaux items ({impactPlan.new_items.length})
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
                Items modifiés ({impactPlan.modified_items.length})
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
                Items supprimés ({impactPlan.deleted_items.length})
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
            <h4 className="font-semibold text-blue-900 mb-2">Résumé</h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>
                • {impactPlan.new_items.length} nouveau
                {impactPlan.new_items.length > 1 ? "x" : ""} item
                {impactPlan.new_items.length > 1 ? "s" : ""}
              </li>
              <li>
                • {impactPlan.modified_items.length} item
                {impactPlan.modified_items.length > 1 ? "s" : ""} modifié
                {impactPlan.modified_items.length > 1 ? "s" : ""}
              </li>
              <li>
                • {impactPlan.deleted_items.length} item
                {impactPlan.deleted_items.length > 1 ? "s" : ""} supprimé
                {impactPlan.deleted_items.length > 1 ? "s" : ""}
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
            Rejeter
          </button>
          <button
            onClick={handleApprove}
            disabled={isProcessing}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isProcessing ? "En cours..." : "Approuver"}
          </button>
        </div>
      </div>
    </div>
  );
}
