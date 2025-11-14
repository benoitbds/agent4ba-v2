"use client";

import { useTranslations } from "next-intl";
import { ClipboardPlus, ChevronRight, ChevronDown, Sparkles, UserCheck, Plus } from "lucide-react";
import { useState } from "react";
import type { WorkItem } from "@/types/events";
import EditWorkItemModal from "./EditWorkItemModal";
import WorkItemFormModal from "./WorkItemFormModal";
import ConfirmDeleteModal from "./ConfirmDeleteModal";
import TestCaseCard from "./TestCaseCard";
import { updateWorkItem, validateWorkItem, generateAcceptanceCriteria, generateTestCases, createWorkItem, deleteWorkItem } from "@/lib/api";
import { toast } from "sonner";

interface BacklogViewProps {
  items: WorkItem[];
  projectId: string;
  onSelectItem?: (item: WorkItem) => void;
  onItemUpdated?: () => void;
}

interface HierarchicalItem {
  item: WorkItem;
  children: HierarchicalItem[];
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

// Fonction pour transformer la liste plate en structure hiérarchique récursive
function buildHierarchy(items: WorkItem[]): HierarchicalItem[] {
  // Créer une map de tous les items par ID pour un accès rapide
  const itemsById = new Map<string, WorkItem>();
  items.forEach((item) => itemsById.set(item.id, item));

  // Créer un map pour grouper les enfants par parent_id
  const childrenByParentId = new Map<string, WorkItem[]>();
  items.forEach((item) => {
    if (item.parent_id) {
      if (!childrenByParentId.has(item.parent_id)) {
        childrenByParentId.set(item.parent_id, []);
      }
      childrenByParentId.get(item.parent_id)!.push(item);
    }
  });

  // Fonction récursive pour construire la hiérarchie
  function buildNode(item: WorkItem): HierarchicalItem {
    const children = childrenByParentId.get(item.id) || [];
    return {
      item,
      children: children.map((child) => buildNode(child)),
    };
  }

  // Trouver les items racines (sans parent) et construire leur arbre
  const rootItems = items.filter((item) => !item.parent_id);
  return rootItems.map((rootItem) => buildNode(rootItem));
}

// Fonction pour déterminer la couleur du badge selon le score
function getBadgeColor(score: number): string {
  if (score > 0.8) return "bg-green-500 text-white";
  if (score > 0.6) return "bg-orange-500 text-white";
  return "bg-red-500 text-white";
}

export default function BacklogView({ items, projectId, onSelectItem, onItemUpdated }: BacklogViewProps) {
  const t = useTranslations();

  // État pour gérer les items dépliés (tous dépliés par défaut)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(() => {
    // Initialiser avec tous les IDs des items qui ont des enfants
    return new Set(items.map((item) => item.id));
  });

  // État pour gérer la modale d'édition avancée (avec validation et AC)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedItemForEdit, setSelectedItemForEdit] = useState<WorkItem | null>(null);

  // État pour gérer la modale de création/édition simple
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [formModalMode, setFormModalMode] = useState<"create" | "edit">("create");
  const [selectedItemForForm, setSelectedItemForForm] = useState<WorkItem | null>(null);

  // État pour gérer la modale de confirmation de suppression
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<WorkItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fonction pour toggler l'état d'un item (feature, story, etc.)
  const toggleItem = (itemId: string) => {
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
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
  const handleValidateWorkItem = async (item: WorkItem) => {
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
      throw error; // Re-throw pour que la modal puisse gérer l'erreur
    }
  };

  // Fonction pour générer les critères d'acceptation
  const handleGenerateAcceptanceCriteria = async (item: WorkItem) => {
    try {
      await generateAcceptanceCriteria(projectId, item.id);
      toast.success(t("backlog.acceptanceCriteriaGenerated", { title: item.title }));
      // Rafraîchir le backlog pour afficher les nouveaux critères
      if (onItemUpdated) {
        onItemUpdated();
      }
    } catch (error) {
      toast.error(t("backlog.acceptanceCriteriaError"));
      console.error("Error generating acceptance criteria:", error);
      throw error; // Re-throw pour que la modal puisse gérer l'erreur
    }
  };

  // Fonction pour générer les cas de test
  const handleGenerateTestCases = async (item: WorkItem) => {
    try {
      // Toast de démarrage
      toast.info(t("backlog.testCasesGenerating", { title: item.title }));

      await generateTestCases(projectId, item.id);
      toast.success(t("backlog.testCasesGenerated", { title: item.title }));
      // Rafraîchir le backlog pour afficher les nouveaux cas de test
      if (onItemUpdated) {
        onItemUpdated();
      }
    } catch (error) {
      toast.error(t("backlog.testCasesError"));
      console.error("Error generating test cases:", error);
      throw error; // Re-throw pour que la modal puisse gérer l'erreur
    }
  };

  // Fonction pour ouvrir la modale de création
  const handleCreateClick = () => {
    setFormModalMode("create");
    setSelectedItemForForm(null);
    setIsFormModalOpen(true);
  };

  // Fonction pour sauvegarder depuis le formulaire (création uniquement)
  const handleFormSave = async (data: {
    type: string;
    title: string;
    description: string | null;
  }) => {
    try {
      if (formModalMode === "create") {
        await createWorkItem(projectId, data);
        toast.success(t("backlog.workItemCreated"));
      } else if (selectedItemForForm) {
        await updateWorkItem(projectId, selectedItemForForm.id, {
          title: data.title,
          description: data.description,
        });
        toast.success(t("backlog.workItemUpdated"));
      }
      // Rafraîchir le backlog
      if (onItemUpdated) {
        onItemUpdated();
      }
    } catch (error) {
      console.error("Error saving work item:", error);
      throw error; // Re-throw pour que la modale puisse afficher l'erreur
    }
  };

  // Fonction pour ouvrir la modale de confirmation de suppression
  const handleDeleteClick = (item: WorkItem, e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    setItemToDelete(item);
    setIsDeleteModalOpen(true);
  };

  // Fonction pour confirmer la suppression
  const handleConfirmDelete = async () => {
    if (!itemToDelete) return;

    setIsDeleting(true);
    try {
      await deleteWorkItem(projectId, itemToDelete.id);
      toast.success(t("backlog.workItemDeleted", { title: itemToDelete.title }));
      setIsDeleteModalOpen(false);
      setItemToDelete(null);
      // Rafraîchir le backlog
      if (onItemUpdated) {
        onItemUpdated();
      }
    } catch (error) {
      toast.error(t("backlog.deleteError"));
      console.error("Error deleting work item:", error);
    } finally {
      setIsDeleting(false);
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

  // Fonction récursive pour rendre un item hiérarchique et ses enfants
  const renderHierarchicalItem = (hierarchicalItem: HierarchicalItem) => {
    const { item, children } = hierarchicalItem;
    const isExpanded = expandedItems.has(item.id);
    const hasChildren = children.length > 0;

    // Si c'est un cas de test, utiliser TestCaseCard
    if (item.type === "test_case") {
      return (
        <div key={item.id}>
          <TestCaseCard
            testCase={item}
            onEdit={handleEditClick}
            onSelect={onSelectItem}
          />
        </div>
      );
    }

    // Pour les autres types (feature, story, task), utiliser le rendu standard
    const investAnalysis = item.attributes?.invest_analysis as
      | InvestAnalysis
      | undefined;

    return (
      <div key={item.id}>
        {/* Carte principale de l'item */}
        <div
          onClick={() => handleEditClick(item)}
          className="p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer"
        >
          <div className="flex items-start gap-3">
            {/* Chevron pour indiquer l'état (seulement si des enfants) */}
            {hasChildren && (
              <div
                className="flex-shrink-0 mt-1 cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleItem(item.id);
                }}
              >
                {isExpanded ? (
                  <ChevronDown className="w-5 h-5 text-gray-600" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-600" />
                )}
              </div>
            )}

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
                  {hasChildren && (
                    <span className="text-gray-500 ml-2">
                      ({children.length})
                    </span>
                  )}
                </h3>
                <span className="text-xs text-gray-500 font-mono">
                  {item.id}
                </span>
                {/* Badge de statut de validation */}
                {item.validation_status === "human_validated" && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded bg-green-100 text-green-800 border border-green-300">
                    <UserCheck className="w-3 h-3" />
                    Validé
                  </span>
                )}
                {item.validation_status === "ia_generated" && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded bg-amber-100 text-amber-800 border border-amber-300">
                    <Sparkles className="w-3 h-3" />
                    IA
                  </span>
                )}
                {item.validation_status === "ia_modified" && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded bg-amber-100 text-amber-800 border border-amber-300">
                    <Sparkles className="w-3 h-3" />
                    IA (Modifié)
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
            {onSelectItem && (
              <div className="flex-shrink-0 flex gap-2">
                {/* Select button for context */}
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
              </div>
            )}
          </div>
        </div>

        {/* Afficher les enfants récursivement si l'item est déplié */}
        {isExpanded && hasChildren && (
          <div className="space-y-3 mt-3">
            {children.map((child) => renderHierarchicalItem(child))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h2 className="text-xl font-semibold">{t("backlog.title")}</h2>
        <button
          onClick={handleCreateClick}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          <Plus className="w-5 h-5" />
          {t("backlog.addWorkItem")}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto pr-2 space-y-3">
        {hierarchicalItems.map((hierarchicalItem) => renderHierarchicalItem(hierarchicalItem))}
      </div>

      {/* Modal d'édition avancée (avec validation et AC) */}
      <EditWorkItemModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSave={handleSaveWorkItem}
        onValidate={handleValidateWorkItem}
        onGenerateAcceptanceCriteria={handleGenerateAcceptanceCriteria}
        onGenerateTestCases={handleGenerateTestCases}
        onDelete={handleDeleteClick}
        item={selectedItemForEdit}
      />

      {/* Modal de création/édition simple */}
      <WorkItemFormModal
        isOpen={isFormModalOpen}
        onClose={() => setIsFormModalOpen(false)}
        onSave={handleFormSave}
        item={selectedItemForForm}
        mode={formModalMode}
        availableItems={items}
      />

      {/* Modal de confirmation de suppression */}
      <ConfirmDeleteModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleConfirmDelete}
        title={t("backlog.confirmDeleteTitle")}
        message={t("backlog.confirmDeleteMessage", { title: itemToDelete?.title || "" })}
        isDeleting={isDeleting}
      />
    </div>
  );
}
