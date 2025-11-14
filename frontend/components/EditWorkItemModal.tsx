"use client";

import { useState, useEffect } from "react";
import { useTranslations } from 'next-intl';
import { CheckCircle, UserCheck, Sparkles, ListChecks } from "lucide-react";
import type { WorkItem } from "@/types/events";

interface EditWorkItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (itemId: string, updatedData: { title: string; description: string | null }) => Promise<void>;
  onValidate?: (item: WorkItem) => Promise<void>;
  onGenerateAcceptanceCriteria?: (item: WorkItem) => Promise<void>;
  item: WorkItem | null;
}

export default function EditWorkItemModal({
  isOpen,
  onClose,
  onSave,
  onValidate,
  onGenerateAcceptanceCriteria,
  item,
}: EditWorkItemModalProps) {
  const t = useTranslations();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isGeneratingAC, setIsGeneratingAC] = useState(false);

  // Initialiser les champs quand l'item change
  useEffect(() => {
    if (item) {
      setTitle(item.title);
      setDescription(item.description || "");
      setError("");
    }
  }, [item]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation basique
    if (!title.trim()) {
      setError(t('editWorkItem.titleRequired'));
      return;
    }

    if (!item) {
      return;
    }

    setIsSaving(true);
    try {
      await onSave(item.id, {
        title: title.trim(),
        description: description.trim() || null,
      });
      handleClose();
    } catch (err) {
      setError(t('editWorkItem.saveFailed'));
      console.error("Failed to save WorkItem:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleValidate = async () => {
    if (!item || !onValidate) return;

    setIsValidating(true);
    try {
      await onValidate(item);
      handleClose();
    } catch (err) {
      setError(t('editWorkItem.validationFailed'));
      console.error("Failed to validate WorkItem:", err);
    } finally {
      setIsValidating(false);
    }
  };

  const handleGenerateAcceptanceCriteria = async () => {
    if (!item || !onGenerateAcceptanceCriteria) return;

    setIsGeneratingAC(true);
    try {
      await onGenerateAcceptanceCriteria(item);
      handleClose();
    } catch (err) {
      setError(t('editWorkItem.acceptanceCriteriaFailed'));
      console.error("Failed to generate acceptance criteria:", err);
    } finally {
      setIsGeneratingAC(false);
    }
  };

  const handleClose = () => {
    setTitle("");
    setDescription("");
    setError("");
    onClose();
  };

  if (!isOpen || !item) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">
          {t('editWorkItem.title')}
        </h2>

        <div className="mb-4 flex items-center gap-2">
          <span className="px-3 py-1 text-sm font-semibold rounded bg-purple-200 text-purple-800">
            {item.type}
          </span>
          <span className="text-sm text-gray-500 font-mono">
            {item.id}
          </span>

          {/* Badge de statut de validation */}
          {item.validation_status === "human_validated" && (
            <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded bg-green-100 text-green-800 border border-green-300">
              <UserCheck className="w-3 h-3" />
              {t('editWorkItem.humanValidated')}
            </span>
          )}
          {item.validation_status === "ia_generated" && (
            <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded bg-amber-100 text-amber-800 border border-amber-300">
              <Sparkles className="w-3 h-3" />
              {t('editWorkItem.iaGenerated')}
            </span>
          )}
          {item.validation_status === "ia_modified" && (
            <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded bg-amber-100 text-amber-800 border border-amber-300">
              <Sparkles className="w-3 h-3" />
              {t('editWorkItem.iaModified')}
            </span>
          )}
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="work-item-title" className="block text-sm font-medium text-gray-700 mb-2">
              {t('editWorkItem.titleLabel')}
            </label>
            <input
              id="work-item-title"
              type="text"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setError("");
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder={t('editWorkItem.titlePlaceholder')}
              autoFocus
              disabled={isSaving}
            />
          </div>

          <div className="mb-6">
            <label htmlFor="work-item-description" className="block text-sm font-medium text-gray-700 mb-2">
              {t('editWorkItem.descriptionLabel')}
            </label>
            <textarea
              id="work-item-description"
              value={description}
              onChange={(e) => {
                setDescription(e.target.value);
                setError("");
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[150px]"
              placeholder={t('editWorkItem.descriptionPlaceholder')}
              disabled={isSaving}
            />
          </div>

          {/* Affichage des critères d'acceptation */}
          {item.acceptance_criteria && item.acceptance_criteria.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">
                {t('editWorkItem.acceptanceCriteria')}
              </h3>
              <ul className="space-y-2">
                {item.acceptance_criteria.map((criterion, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg border border-blue-200"
                  >
                    <span className="text-blue-600 font-semibold mt-0.5">✓</span>
                    <span className="text-sm text-gray-800 flex-1">{criterion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {error && (
            <p className="mb-4 text-sm text-red-600">{error}</p>
          )}

          <div className="flex justify-between items-center gap-3">
            {/* Boutons d'actions à gauche */}
            <div className="flex gap-3">
              {/* Bouton de validation (si applicable) */}
              {onValidate && (item.validation_status === "ia_generated" || item.validation_status === "ia_modified") && (
                <button
                  type="button"
                  onClick={handleValidate}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 inline-flex items-center gap-2"
                  disabled={isSaving || isValidating || isGeneratingAC}
                >
                  <CheckCircle className="w-4 h-4" />
                  {isValidating ? t('editWorkItem.validating') : t('editWorkItem.validate')}
                </button>
              )}

              {/* Bouton de génération des critères d'acceptation (uniquement pour les stories) */}
              {onGenerateAcceptanceCriteria && item.type === "story" && (
                <button
                  type="button"
                  onClick={handleGenerateAcceptanceCriteria}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 inline-flex items-center gap-2"
                  disabled={isSaving || isValidating || isGeneratingAC}
                >
                  <ListChecks className="w-4 h-4" />
                  {isGeneratingAC ? t('editWorkItem.generatingAC') : t('editWorkItem.generateAC')}
                </button>
              )}
            </div>

            <div className="flex-1"></div>

            {/* Boutons Annuler et Sauvegarder à droite */}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50"
                disabled={isSaving || isValidating || isGeneratingAC}
              >
                {t('editWorkItem.cancel')}
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50"
                disabled={isSaving || isValidating || isGeneratingAC}
              >
                {isSaving ? t('editWorkItem.saving') : t('editWorkItem.save')}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
