"use client";

import { useTranslations } from "next-intl";
import { ClipboardPlus, ChevronRight, ChevronDown, Sparkles, CheckCircle } from "lucide-react";
import { useState } from "react";
import type { WorkItem } from "@/types/events";
import EditWorkItemModal from "./EditWorkItemModal";
import { updateWorkItem, validateWorkItem } from "@/lib/api";
import { toast } from "sonner";

interface BacklogViewProps {
  items: WorkItem[];
  projectId: string;
  onSelectItem?: (item: WorkItem) => void;
  onItemUpdated?: () => void;
}

interface HierarchicalItem {
  item: WorkItem;
  children: WorkItem[];
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

// Fonction pour transformer la liste plate en structure hiérarchique
function buildHierarchy(items: WorkItem[]): HierarchicalItem[] {
  // Séparer les features (items sans parent) et les stories/tasks (avec parent)
  const rootItems = items.filter((item) => !item.parent_id);
  const childItems = items.filter((item) => item.parent_id);

  // Créer un map pour un accès rapide aux enfants par parent_id
  const childrenByParentId = new Map<string, WorkItem[]>();
  childItems.forEach((child) => {
    const parentId = child.parent_id!;
    if (!childrenByParentId.has(parentId)) {
      childrenByParentId.set(parentId, []);
    }
    childrenByParentId.get(parentId)!.push(child);
  });

  // Construire la structure hiérarchique
  return rootItems.map((rootItem) => ({
    item: rootItem,
    children: childrenByParentId.get(rootItem.id) || [],
  }));
}

// Fonction pour déterminer la couleur du badge selon le score
function getBadgeColor(score: number): string {
  if (score > 0.8) return "bg-green-500 text-white";
  if (score > 0.6) return "bg-orange-500 text-white";
  return "bg-red-500 text-white";
}

export default function BacklogView({ items, projectId, onSelectItem, onItemUpdated }: BacklogViewProps) {
  const t = useTranslations();

  // État pour gérer les features dépliées (toutes dépliées par défaut)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(() => {
    // Initialiser avec tous les IDs des features
    const allFeatureIds = items
      .filter((item) => !item.parent_id)
      .map((item) => item.id);
    return new Set(allFeatureIds);
  });

  // État pour gérer la modale d'édition
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedItemForEdit, setSelectedItemForEdit] = useState<WorkItem | null>(null);

  // Fonction pour toggler l'état d'une feature
  const toggleFeature = (featureId: string) => {
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(featureId)) {
        newSet.delete(featureId);
      } else {
        newSet.add(featureId);
      }
      return newSet;
    });
  };

  // Fonction pour ouvrir la modale d'édition
  const handleEditClick = (item: WorkItem, e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    setSelectedItemForEdit(item);
    setIsEditModalOpen(true);
  };

  // Fonction pour sauvegarder les modifications
  const handleSaveWorkItem = async (
    itemId: string,
    updatedData: { title: string; description: string | null }
  ) => {
    await updateWorkItem(projectId, itemId, updatedData);
    // Appeler le callback pour rafraîchir le backlog
    if (onItemUpdated) {
      onItemUpdated();
    }
  };

  // Fonction pour valider un WorkItem
  const handleValidateWorkItem = async (item: WorkItem, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await validateWorkItem(projectId, item.id);
      toast.success(t("backlog.validationSuccess", { title: item.title }));
      // Rafraîchir le backlog pour afficher le nouveau statut
      if (onItemUpdated) {
        onItemUpdated();
      }
    } catch (error) {
      toast.error(t("backlog.validationError"));
      console.error("Error validating work item:", error);
    }
  };

  if (items.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <h2 className="text-xl font-semibold mb-4 flex-shrink-0">{t("backlog.title")}</h2>
        <div className="text-center py-12 flex-1">
          <p className="text-gray-500">{t("backlog.empty")}</p>
        </div>
      </div>
    );
  }

  // Construire la structure hiérarchique
  const hierarchicalItems = buildHierarchy(items);

  // Fonction pour rendre un WorkItem (réutilisable pour parent et enfants)
  const renderWorkItem = (item: WorkItem, isChild: boolean = false) => {
    const investAnalysis = item.attributes?.invest_analysis as
      | InvestAnalysis
      | undefined;

    return (
      <div
        key={item.id}
        onClick={() => handleEditClick(item)}
        className={`p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer ${
          isChild ? "ml-8" : ""
        }`}
      >
        <div className="flex items-start gap-3">
          <span
            className={`px-2 py-1 text-xs font-semibold rounded flex-shrink-0 ${
              item.type === "feature"
                ? "bg-purple-200 text-purple-800"
                : item.type === "story"
                ? "bg-blue-200 text-blue-800"
                : "bg-green-200 text-green-800"
            }`}
          >
            {item.type}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-gray-900">
                {item.title}
              </h3>
              <span className="text-xs text-gray-500 font-mono">
                {item.id}
              </span>
              {/* Badge IA pour les items générés ou modifiés par l'IA */}
              {(item.validation_status === "ia_generated" || item.validation_status === "ia_modified") && (
                <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded bg-amber-100 text-amber-800 border border-amber-300">
                  <Sparkles className="w-3 h-3" />
                  {item.validation_status === "ia_modified" ? "IA (Modifié)" : "IA"}
                </span>
              )}
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
                      title={`${t(`invest.${criterion}`)}: ${data.reason}`}
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
                            {t(`invest.${criterion}`)}
                          </div>
                          <div className="mb-1">
                            {t("timeline.score")} {(data.score * 100).toFixed(0)}%
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
                    {t("backlog.priority")} {item.attributes.priority}
                  </span>
                )}
                {item.attributes.points !== undefined && (
                  <span className="px-2 py-1 bg-gray-100 rounded">
                    {t("backlog.points")} {item.attributes.points}
                  </span>
                )}
                {item.attributes.status && (
                  <span className="px-2 py-1 bg-gray-100 rounded">
                    {t("backlog.status")} {item.attributes.status}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Boutons d'action */}
          <div className="flex-shrink-0 flex gap-2">
            {/* Bouton de validation (pour les items générés ou modifiés par l'IA) */}
            {(item.validation_status === "ia_generated" || item.validation_status === "ia_modified") && (
              <button
                onClick={(e) => handleValidateWorkItem(item, e)}
                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                title={t("backlog.validateItem")}
              >
                <CheckCircle className="w-5 h-5" />
              </button>
            )}
            {/* Select button for context */}
            {onSelectItem && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectItem(item);
                }}
                className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-green-500"
                title={t("backlog.addToContext")}
              >
                <ClipboardPlus className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xl font-semibold mb-4 flex-shrink-0">{t("backlog.title")}</h2>
      <div className="flex-1 overflow-y-auto pr-2 space-y-3">
        {hierarchicalItems.map((hierarchicalItem) => {
          const isExpanded = expandedItems.has(hierarchicalItem.item.id);
          const childrenCount = hierarchicalItem.children.length;

          return (
            <div key={hierarchicalItem.item.id}>
              {/* Afficher la feature parente avec chevron */}
              <div className="relative">
                <div
                  onClick={() => handleEditClick(hierarchicalItem.item)}
                  className={`p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer`}
                >
                  <div className="flex items-start gap-3">
                    {/* Chevron pour indiquer l'état */}
                    <div
                      className="flex-shrink-0 mt-1 cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFeature(hierarchicalItem.item.id);
                      }}
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-gray-600" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-600" />
                      )}
                    </div>

                    <span
                      className={`px-2 py-1 text-xs font-semibold rounded flex-shrink-0 ${
                        hierarchicalItem.item.type === "feature"
                          ? "bg-purple-200 text-purple-800"
                          : hierarchicalItem.item.type === "story"
                          ? "bg-blue-200 text-blue-800"
                          : "bg-green-200 text-green-800"
                      }`}
                    >
                      {hierarchicalItem.item.type}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-900">
                          {hierarchicalItem.item.title}
                          {childrenCount > 0 && (
                            <span className="text-gray-500 ml-2">
                              ({childrenCount})
                            </span>
                          )}
                        </h3>
                        <span className="text-xs text-gray-500 font-mono">
                          {hierarchicalItem.item.id}
                        </span>
                        {/* Badge IA pour les items générés ou modifiés par l'IA */}
                        {(hierarchicalItem.item.validation_status === "ia_generated" || hierarchicalItem.item.validation_status === "ia_modified") && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded bg-amber-100 text-amber-800 border border-amber-300">
                            <Sparkles className="w-3 h-3" />
                            {hierarchicalItem.item.validation_status === "ia_modified" ? "IA (Modifié)" : "IA"}
                          </span>
                        )}
                      </div>
                      {hierarchicalItem.item.description && (
                        <p className="text-sm text-gray-600 mt-1">
                          {hierarchicalItem.item.description}
                        </p>
                      )}

                      {/* INVEST Analysis Badges */}
                      {(() => {
                        const investAnalysis = hierarchicalItem.item.attributes
                          ?.invest_analysis as InvestAnalysis | undefined;
                        return (
                          investAnalysis && (
                            <div className="flex gap-1 mt-2">
                              {Object.entries(investAnalysis).map(
                                ([criterion, data]) => (
                                  <div
                                    key={criterion}
                                    className="group relative"
                                    title={`${t(`invest.${criterion}`)}: ${data.reason}`}
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
                                          {t(`invest.${criterion}`)}
                                        </div>
                                        <div className="mb-1">
                                          {t("timeline.score")}{" "}
                                          {(data.score * 100).toFixed(0)}%
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
                          )
                        );
                      })()}

                      {/* Autres attributs */}
                      {hierarchicalItem.item.attributes && (
                        <div className="flex gap-2 mt-2 text-xs">
                          {hierarchicalItem.item.attributes.priority && (
                            <span className="px-2 py-1 bg-gray-100 rounded">
                              {t("backlog.priority")}{" "}
                              {hierarchicalItem.item.attributes.priority}
                            </span>
                          )}
                          {hierarchicalItem.item.attributes.points !==
                            undefined && (
                            <span className="px-2 py-1 bg-gray-100 rounded">
                              {t("backlog.points")}{" "}
                              {hierarchicalItem.item.attributes.points}
                            </span>
                          )}
                          {hierarchicalItem.item.attributes.status && (
                            <span className="px-2 py-1 bg-gray-100 rounded">
                              {t("backlog.status")}{" "}
                              {hierarchicalItem.item.attributes.status}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Boutons d'action */}
                    <div className="flex-shrink-0 flex gap-2">
                      {/* Bouton de validation (pour les items générés ou modifiés par l'IA) */}
                      {(hierarchicalItem.item.validation_status === "ia_generated" || hierarchicalItem.item.validation_status === "ia_modified") && (
                        <button
                          onClick={(e) => handleValidateWorkItem(hierarchicalItem.item, e)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                          title={t("backlog.validateItem")}
                        >
                          <CheckCircle className="w-5 h-5" />
                        </button>
                      )}
                      {/* Select button for context */}
                      {onSelectItem && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectItem(hierarchicalItem.item);
                          }}
                          className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-green-500"
                          title={t("backlog.addToContext")}
                        >
                          <ClipboardPlus className="w-5 h-5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Afficher les stories enfants avec indentation si la feature est dépliée */}
              {isExpanded && hierarchicalItem.children.length > 0 && (
                <div className="space-y-3 mt-3">
                  {hierarchicalItem.children.map((child) =>
                    renderWorkItem(child, true)
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Modal d'édition */}
      <EditWorkItemModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSave={handleSaveWorkItem}
        item={selectedItemForEdit}
      />
    </div>
  );
}
