"use client";

import { useState } from "react";

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
  const [projectId, setProjectId] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validation basique
    if (!projectId.trim()) {
      setError("Le nom du projet est requis");
      return;
    }

    // Validation du format (pas d'espaces, caractères spéciaux limités)
    const validProjectIdRegex = /^[a-zA-Z0-9_-]+$/;
    if (!validProjectIdRegex.test(projectId)) {
      setError("Le nom du projet ne peut contenir que des lettres, chiffres, tirets et underscores");
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
        <h2 className="text-2xl font-bold mb-4 text-gray-800">Créer un nouveau projet</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="project-id" className="block text-sm font-medium text-gray-700 mb-2">
              Nom du projet
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
              placeholder="mon-projet"
              autoFocus
            />
            {error && (
              <p className="mt-2 text-sm text-red-600">{error}</p>
            )}
            <p className="mt-2 text-sm text-gray-500">
              Utilisez uniquement des lettres, chiffres, tirets (-) et underscores (_)
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Créer
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
