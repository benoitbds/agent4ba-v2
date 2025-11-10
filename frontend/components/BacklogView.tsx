"use client";

import type { WorkItem } from "@/types/events";

interface BacklogViewProps {
  items: WorkItem[];
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

export default function BacklogView({ items }: BacklogViewProps) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <h2 className="text-xl font-semibold mb-4 flex-shrink-0">Backlog du projet</h2>
        <div className="text-center py-12 flex-1">
          <p className="text-gray-500">Aucun item dans le backlog</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xl font-semibold mb-4 flex-shrink-0">Backlog du projet</h2>
      <div className="flex-1 overflow-y-auto pr-2 space-y-3">
        {items.map((item) => {
          const investAnalysis = item.attributes?.invest_analysis as
            | InvestAnalysis
            | undefined;

          return (
            <div
              key={item.id}
              className="p-4 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
            >
              <div className="flex items-start gap-3">
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
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">
                      {item.title}
                    </h3>
                    <span className="text-xs text-gray-500 font-mono">
                      {item.id}
                    </span>
                  </div>
                  {item.description && (
                    <p className="text-sm text-gray-600 mt-1">
                      {item.description}
                    </p>
                  )}

                  {/* INVEST Analysis Badges */}
                  {investAnalysis && (
                    <div className="flex gap-1 mt-2">
                      {Object.entries(investAnalysis).map(
                        ([criterion, data]) => (
                          <div
                            key={criterion}
                            className="group relative"
                            title={`${INVEST_LABELS[criterion]}: ${data.reason}`}
                          >
                            <span
                              className={`px-2 py-1 text-xs font-bold rounded cursor-help ${getBadgeColor(data.score)}`}
                            >
                              {criterion}
                            </span>
                            {/* Tooltip au survol */}
                            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-10 w-64">
                              <div className="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 shadow-lg">
                                <div className="font-bold mb-1">
                                  {INVEST_LABELS[criterion]}
                                </div>
                                <div className="mb-1">
                                  Score: {(data.score * 100).toFixed(0)}%
                                </div>
                                <div className="text-gray-300">
                                  {data.reason}
                                </div>
                              </div>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}

                  {/* Autres attributs */}
                  {item.attributes && (
                    <div className="flex gap-2 mt-2 text-xs">
                      {item.attributes.priority && (
                        <span className="px-2 py-1 bg-gray-100 rounded">
                          Priorité: {item.attributes.priority}
                        </span>
                      )}
                      {item.attributes.points !== undefined && (
                        <span className="px-2 py-1 bg-gray-100 rounded">
                          Points: {item.attributes.points}
                        </span>
                      )}
                      {item.attributes.status && (
                        <span className="px-2 py-1 bg-gray-100 rounded">
                          Statut: {item.attributes.status}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
