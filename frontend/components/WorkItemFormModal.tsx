"use client";

import { useState, useEffect } from "react";
import { useTranslations } from 'next-intl';
import type { WorkItem } from "@/types/events";

interface WorkItemFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: {
    type: string;
    title: string;
    description: string | null;
    parent_id?: string | null;
  }) => Promise<void>;
  item?: WorkItem | null; // Si fourni, mode édition ; sinon, mode création
  mode: "create" | "edit";
}

export default function WorkItemFormModal({
  isOpen,
  onClose,
  onSave,
  item,
  mode,
}: WorkItemFormModalProps) {
  const t = useTranslations();
  const [type, setType] = useState("feature");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Initialiser les champs quand l'item change (mode édition)
  useEffect(() => {
    if (mode === "edit" && item) {
      setType(item.type);
      setTitle(item.title);
      setDescription(item.description || "");
      setError("");
    } else if (mode === "create") {
      // Réinitialiser pour la création
      setType("feature");
      setTitle("");
      setDescription("");
      setError("");
    }
  }, [item, mode, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation basique
    if (!title.trim()) {
      setError(t('workItemForm.titleRequired'));
      return;
    }

    setIsSaving(true);
    try {
      await onSave({
        type,
        title: title.trim(),
        description: description.trim() || null,
      });
      handleClose();
    } catch (err) {
      setError(mode === "create"
        ? t('workItemForm.createFailed')
        : t('workItemForm.updateFailed')
      );
      console.error(`Failed to ${mode} WorkItem:`, err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    setType("feature");
    setTitle("");
    setDescription("");
    setError("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">
          {mode === "create"
            ? t('workItemForm.createTitle')
            : t('workItemForm.editTitle')
          }
        </h2>

        <form onSubmit={handleSubmit}>
          {/* Champ Type - visible seulement en mode création */}
          {mode === "create" && (
            <div className="mb-4">
              <label htmlFor="work-item-type" className="block text-sm font-medium text-gray-700 mb-2">
                {t('workItemForm.typeLabel')}
              </label>
              <select
                id="work-item-type"
                value={type}
                onChange={(e) => {
                  setType(e.target.value);
                  setError("");
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isSaving}
              >
                <option value="feature">Feature</option>
                <option value="story">Story</option>
                <option value="task">Task</option>
                <option value="bug">Bug</option>
              </select>
            </div>
          )}

          {/* Affichage du type en mode édition */}
          {mode === "edit" && item && (
            <div className="mb-4 flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">
                {t('workItemForm.typeLabel')}:
              </span>
              <span className={`px-3 py-1 text-sm font-semibold rounded ${
                item.type === "feature"
                  ? "bg-purple-200 text-purple-800"
                  : item.type === "story"
                  ? "bg-blue-200 text-blue-800"
                  : item.type === "task"
                  ? "bg-green-200 text-green-800"
                  : "bg-red-200 text-red-800"
              }`}>
                {item.type}
              </span>
              <span className="text-sm text-gray-500 font-mono">
                {item.id}
              </span>
            </div>
          )}

          {/* Champ Titre */}
          <div className="mb-4">
            <label htmlFor="work-item-title" className="block text-sm font-medium text-gray-700 mb-2">
              {t('workItemForm.titleLabel')}
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
              placeholder={t('workItemForm.titlePlaceholder')}
              autoFocus
              disabled={isSaving}
            />
          </div>

          {/* Champ Description */}
          <div className="mb-6">
            <label htmlFor="work-item-description" className="block text-sm font-medium text-gray-700 mb-2">
              {t('workItemForm.descriptionLabel')}
            </label>
            <textarea
              id="work-item-description"
              value={description}
              onChange={(e) => {
                setDescription(e.target.value);
                setError("");
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[150px]"
              placeholder={t('workItemForm.descriptionPlaceholder')}
              disabled={isSaving}
            />
          </div>

          {error && (
            <p className="mb-4 text-sm text-red-600">{error}</p>
          )}

          {/* Boutons */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50"
              disabled={isSaving}
            >
              {t('workItemForm.cancel')}
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
              disabled={isSaving}
            >
              {isSaving
                ? t('workItemForm.saving')
                : mode === "create"
                  ? t('workItemForm.create')
                  : t('workItemForm.save')
              }
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
