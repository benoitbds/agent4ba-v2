"use client";

import { useState } from "react";
import type { ToolRunState } from "@/types/events";

interface ToolRunViewProps {
  toolRun: ToolRunState;
}

export default function ToolRunView({ toolRun }: ToolRunViewProps) {
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);

  const getStatusBadge = () => {
    switch (toolRun.status) {
      case "completed":
        return (
          <span className="text-xs font-medium px-2 py-1 rounded bg-green-100 text-green-700">
            ✓ Terminé
          </span>
        );
      case "error":
        return (
          <span className="text-xs font-medium px-2 py-1 rounded bg-red-100 text-red-700">
            ⚠ Erreur
          </span>
        );
      case "running":
        return (
          <span className="text-xs font-medium px-2 py-1 rounded bg-blue-100 text-blue-700 flex items-center gap-1">
            <span className="animate-spin inline-block w-3 h-3 border-2 border-blue-700 border-t-transparent rounded-full" />
            En cours
          </span>
        );
      default:
        return null;
    }
  };

  const hasDetails = toolRun.details && Object.keys(toolRun.details).length > 0;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3">
        {/* Icône */}
        <div className="text-2xl flex-shrink-0">{toolRun.tool_icon}</div>

        {/* Contenu principal */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <h4 className="font-semibold text-gray-900">{toolRun.tool_name}</h4>
            {getStatusBadge()}
          </div>
          <p className="text-xs text-gray-500">{toolRun.description}</p>

          {/* Détails dépliables */}
          {hasDetails && (
            <div className="mt-3">
              <button
                onClick={() => setIsDetailsOpen(!isDetailsOpen)}
                className="text-xs text-gray-600 hover:text-gray-900 font-medium flex items-center gap-1"
              >
                <span>{isDetailsOpen ? "▼" : "▶"}</span>
                Voir les détails
              </button>

              {isDetailsOpen && (
                <div className="mt-2 space-y-2">
                  {toolRun.details.model && (
                    <div className="text-xs">
                      <span className="font-medium text-gray-700">Modèle :</span>{" "}
                      <span className="text-gray-600">{(toolRun.details.model as string)}</span>
                    </div>
                  )}
                  {toolRun.details.temperature !== undefined && (
                    <div className="text-xs">
                      <span className="font-medium text-gray-700">Température :</span>{" "}
                      <span className="text-gray-600">{(toolRun.details.temperature as number)}</span>
                    </div>
                  )}
                  {toolRun.details.chunks_retrieved !== undefined && (
                    <div className="text-xs">
                      <span className="font-medium text-gray-700">Chunks récupérés :</span>{" "}
                      <span className="text-gray-600">{(toolRun.details.chunks_retrieved as number)}</span>
                    </div>
                  )}
                  {toolRun.details.documents_loaded !== undefined && (
                    <div className="text-xs">
                      <span className="font-medium text-gray-700">Documents chargés :</span>{" "}
                      <span className="text-gray-600">{(toolRun.details.documents_loaded as number)}</span>
                    </div>
                  )}
                  {toolRun.details.items_count !== undefined && (
                    <div className="text-xs">
                      <span className="font-medium text-gray-700">Items du backlog :</span>{" "}
                      <span className="text-gray-600">{(toolRun.details.items_count as number)}</span>
                    </div>
                  )}
                  {toolRun.details.response_length !== undefined && (
                    <div className="text-xs">
                      <span className="font-medium text-gray-700">Longueur de la réponse :</span>{" "}
                      <span className="text-gray-600">{(toolRun.details.response_length as number)} caractères</span>
                    </div>
                  )}

                  {toolRun.details.prompt_preview && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-gray-600 hover:text-gray-900 font-medium">
                        Voir le prompt
                      </summary>
                      <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                        {(toolRun.details.prompt_preview as string)}
                      </pre>
                    </details>
                  )}

                  {toolRun.details.response_preview && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-gray-600 hover:text-gray-900 font-medium">
                        Voir la réponse
                      </summary>
                      <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                        {(toolRun.details.response_preview as string)}
                      </pre>
                    </details>
                  )}

                  {/* Affichage de l'erreur si présente */}
                  {toolRun.details.error && (
                    <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded">
                      <p className="text-xs font-medium text-red-700">Erreur :</p>
                      <p className="text-xs text-red-600 mt-1">{(toolRun.details.error as string)}</p>
                    </div>
                  )}

                  {/* Affichage brut des autres détails */}
                  {Object.keys(toolRun.details).some(
                    (key) =>
                      ![
                        "model",
                        "temperature",
                        "chunks_retrieved",
                        "documents_loaded",
                        "items_count",
                        "response_length",
                        "prompt_preview",
                        "response_preview",
                        "error",
                      ].includes(key)
                  ) && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-gray-600 hover:text-gray-900 font-medium">
                        Autres détails
                      </summary>
                      <pre className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded text-xs overflow-x-auto">
                        {JSON.stringify(
                          Object.fromEntries(
                            Object.entries(toolRun.details).filter(
                              ([key]) =>
                                ![
                                  "model",
                                  "temperature",
                                  "chunks_retrieved",
                                  "documents_loaded",
                                  "items_count",
                                  "response_length",
                                  "prompt_preview",
                                  "response_preview",
                                  "error",
                                ].includes(key)
                            )
                          ),
                          null,
                          2
                        )}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Timestamp */}
          <p className="text-xs text-gray-400 mt-2">
            {toolRun.started_at.toLocaleTimeString()}
            {toolRun.completed_at && ` → ${toolRun.completed_at.toLocaleTimeString()}`}
          </p>
        </div>
      </div>
    </div>
  );
}
