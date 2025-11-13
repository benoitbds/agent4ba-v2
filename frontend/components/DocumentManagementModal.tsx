"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Trash2, Check, X, Plus, ClipboardPlus } from "lucide-react";
import UploadDocumentModal from "./UploadDocumentModal";
import { deleteDocument } from "@/lib/api";

interface DocumentManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  documents: string[];
  onDocumentsChange: () => void;
  onSelectDocument: (documentName: string) => void;
}

export default function DocumentManagementModal({
  isOpen,
  onClose,
  projectId,
  documents,
  onDocumentsChange,
  onSelectDocument,
}: DocumentManagementModalProps) {
  const t = useTranslations();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [deletingDocument, setDeletingDocument] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const handleDeleteDocument = async (documentName: string) => {
    if (confirmDelete !== documentName) {
      setConfirmDelete(documentName);
      return;
    }

    setDeletingDocument(documentName);
    try {
      await deleteDocument(projectId, documentName);
      onDocumentsChange();
      setConfirmDelete(null);
    } catch (error) {
      console.error("Error deleting document:", error);
      alert(
        error instanceof Error
          ? error.message
          : t("documents.deleteError")
      );
    } finally {
      setDeletingDocument(null);
    }
  };

  const handleSelectDocument = (documentName: string) => {
    onSelectDocument(documentName);
    onClose();
  };

  const handleUploadSuccess = () => {
    onDocumentsChange();
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-2xl font-bold text-gray-900">
              {t("documents.title")}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Add Document Button */}
            <div className="mb-4">
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                <Plus className="w-5 h-5" />
                {t("documents.add")}
              </button>
            </div>

            {/* Documents List */}
            {documents.length === 0 ? (
              <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-gray-500 text-sm">
                  {t("documents.empty")}
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((docName) => (
                  <div
                    key={docName}
                    className="p-4 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-3">
                      {/* Document Icon and Name */}
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <svg
                          className="w-5 h-5 text-red-600 flex-shrink-0"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                            clipRule="evenodd"
                          />
                        </svg>
                        <span className="text-sm font-medium text-gray-900 truncate">
                          {docName}
                        </span>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {/* Select Button */}
                        <button
                          onClick={() => handleSelectDocument(docName)}
                          className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-green-500"
                          title={t("documents.select")}
                        >
                          <ClipboardPlus className="w-5 h-5" />
                        </button>

                        {/* Delete Button */}
                        {confirmDelete === docName ? (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-red-600 font-medium">
                              {t("documents.confirmDelete")}
                            </span>
                            <button
                              onClick={() => handleDeleteDocument(docName)}
                              disabled={deletingDocument === docName}
                              className="p-2 text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50"
                              title={t("documents.confirmDeleteAction")}
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setConfirmDelete(null)}
                              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500"
                              title={t("documents.cancel")}
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleDeleteDocument(docName)}
                            disabled={deletingDocument === docName}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50"
                            title={t("documents.delete")}
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end p-6 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            >
              {t("documents.close")}
            </button>
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      <UploadDocumentModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        projectId={projectId}
        onUploadSuccess={handleUploadSuccess}
      />
    </>
  );
}
