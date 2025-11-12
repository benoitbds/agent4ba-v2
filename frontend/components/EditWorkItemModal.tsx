"use client";

import { useState, useEffect } from "react";
import { useTranslations } from 'next-intl';
import type { WorkItem } from "@/types/events";

interface EditWorkItemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (itemId: string, updatedData: { title: string; description: string | null }) => Promise<void>;
  item: WorkItem | null;
}

export default function EditWorkItemModal({
  isOpen,
  onClose,
  onSave,
  item,
}: EditWorkItemModalProps) {
  const t = useTranslations();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

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

        <div className="mb-4">
          <span className="px-3 py-1 text-sm font-semibold rounded bg-purple-200 text-purple-800">
            {item.type}
          </span>
          <span className="ml-3 text-sm text-gray-500 font-mono">
            {item.id}
          </span>
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

          {error && (
            <p className="mb-4 text-sm text-red-600">{error}</p>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50"
              disabled={isSaving}
            >
              {t('editWorkItem.cancel')}
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
              disabled={isSaving}
            >
              {isSaving ? t('editWorkItem.saving') : t('editWorkItem.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
