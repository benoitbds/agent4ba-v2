"use client";

import { useState } from "react";
import { useTranslations } from 'next-intl';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateProject: (projectId: string) => void;
}

export default function CreateProjectModal({
  isOpen,
  onClose,
  onCreateProject,
}: CreateProjectModalProps) {
  const t = useTranslations();
  const [projectId, setProjectId] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validation basique
    if (!projectId.trim()) {
      setError(t('createProject.nameRequired'));
      return;
    }

    // Validation du format (pas d'espaces, caractères spéciaux limités)
    const validProjectIdRegex = /^[a-zA-Z0-9_-]+$/;
    if (!validProjectIdRegex.test(projectId)) {
      setError(t('createProject.invalidFormat'));
      return;
    }

    onCreateProject(projectId);
    setProjectId("");
    setError("");
  };

  const handleClose = () => {
    setProjectId("");
    setError("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">{t('createProject.title')}</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="project-id" className="block text-sm font-medium text-gray-700 mb-2">
              {t('createProject.nameLabel')}
            </label>
            <input
              id="project-id"
              type="text"
              value={projectId}
              onChange={(e) => {
                setProjectId(e.target.value);
                setError("");
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder={t('createProject.placeholder')}
              autoFocus
            />
            {error && (
              <p className="mt-2 text-sm text-red-600">{error}</p>
            )}
            <p className="mt-2 text-sm text-gray-500">
              {t('createProject.hint')}
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors"
            >
              {t('createProject.cancel')}
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {t('createProject.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
