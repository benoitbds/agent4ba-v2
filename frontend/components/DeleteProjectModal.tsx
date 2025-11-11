"use client";

import { useState } from "react";
import { useTranslations } from 'next-intl';
import { AlertTriangle } from "lucide-react";

interface DeleteProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDeleteProject: () => void;
  projectName: string;
}

export default function DeleteProjectModal({
  isOpen,
  onClose,
  onDeleteProject,
  projectName,
}: DeleteProjectModalProps) {
  const t = useTranslations();
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDeleteProject();
      onClose();
    } catch (error) {
      console.error("Error deleting project:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-800">
            {t('deleteProject.title')}
          </h2>
        </div>

        <div className="mb-6">
          <p className="text-gray-700 mb-3">
            {t('deleteProject.confirmMessage')}{" "}
            <span className="font-semibold text-gray-900">
              &quot;{projectName}&quot;
            </span>{" "}
            ?
          </p>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800 font-semibold">
              {t('deleteProject.warning')}
            </p>
            <p className="text-sm text-red-700 mt-2">
              {t('deleteProject.warningDetails')}
            </p>
            <ul className="text-sm text-red-700 mt-2 ml-4 list-disc">
              <li>{t('deleteProject.backlogData')}</li>
              <li>{t('deleteProject.timelineHistory')}</li>
              <li>{t('deleteProject.uploadedDocuments')}</li>
            </ul>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('deleteProject.cancel')}
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isDeleting}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? t('deleteProject.deleting') : t('deleteProject.confirm')}
          </button>
        </div>
      </div>
    </div>
  );
}
