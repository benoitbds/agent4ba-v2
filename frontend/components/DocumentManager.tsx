"use client";

import { useState } from "react";
import UploadDocumentModal from "./UploadDocumentModal";

interface DocumentManagerProps {
  projectId: string;
  documents: string[];
  onUploadSuccess: () => void;
}

export default function DocumentManager({
  projectId,
  documents,
  onUploadSuccess,
}: DocumentManagerProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleUploadSuccess = () => {
    onUploadSuccess();
  };

  return (
    <div className="space-y-4">
      {/* Header with title and add button */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Documents du Projet</h2>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 hover:bg-blue-700 text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          title="Ajouter un document"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
      </div>

      {/* Documents List */}
      <div>
        {documents.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
            <p className="text-gray-500 text-sm">
              Pour commencer, ajoutez un document en cliquant sur le bouton +
            </p>
          </div>
        ) : (
          <>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Documents existants
            </h3>
            <ul className="space-y-2">
              {documents.map((docName) => (
                <li
                  key={docName}
                  className="p-3 bg-white rounded border border-gray-200 hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <svg
                      className="w-5 h-5 text-red-600"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className="text-sm font-medium text-gray-900">
                      {docName}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      {/* Upload Modal */}
      <UploadDocumentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        projectId={projectId}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
}
