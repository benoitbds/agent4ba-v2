"use client";

import { useState, useRef } from "react";

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
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Vérifier le type de fichier
      if (file.type !== "application/pdf") {
        setUploadStatus("error");
        setStatusMessage("Seuls les fichiers PDF sont acceptés");
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setUploadStatus("idle");
      setStatusMessage("");
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadStatus("error");
      setStatusMessage("Veuillez sélectionner un fichier");
      return;
    }

    setUploadStatus("uploading");
    setStatusMessage("Upload en cours...");

    try {
      // Dynamically import uploadDocument to avoid circular dependency
      const { uploadDocument } = await import("@/lib/api");

      const response = await uploadDocument(projectId, selectedFile);
      setUploadStatus("success");
      setStatusMessage(response.message);
      setSelectedFile(null);

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      // Notify parent component to refresh documents list
      onUploadSuccess();
    } catch (error) {
      setUploadStatus("error");
      setStatusMessage(
        error instanceof Error
          ? error.message
          : "Erreur lors de l'upload du fichier"
      );
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold mb-4">Documents du Projet</h2>

      {/* Upload Form */}
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Uploader un document
        </h3>
        <div className="space-y-3">
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              onChange={handleFileSelect}
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100
                cursor-pointer"
              disabled={uploadStatus === "uploading"}
            />
            <p className="mt-1 text-xs text-gray-500">
              Seuls les fichiers PDF sont acceptés
            </p>
          </div>

          {selectedFile && (
            <div className="text-sm text-gray-700 bg-white p-2 rounded border border-gray-200">
              Fichier sélectionné: <strong>{selectedFile.name}</strong> (
              {(selectedFile.size / 1024).toFixed(2)} KB)
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploadStatus === "uploading"}
            className={`w-full py-2 px-4 rounded font-semibold text-white transition-colors ${
              !selectedFile || uploadStatus === "uploading"
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {uploadStatus === "uploading" ? "Upload en cours..." : "Uploader"}
          </button>

          {/* Status Message */}
          {statusMessage && (
            <div
              className={`p-3 rounded text-sm ${
                uploadStatus === "error"
                  ? "bg-red-100 border border-red-300 text-red-800"
                  : uploadStatus === "success"
                  ? "bg-green-100 border border-green-300 text-green-800"
                  : "bg-blue-100 border border-blue-300 text-blue-800"
              }`}
            >
              {statusMessage}
            </div>
          )}
        </div>
      </div>

      {/* Documents List */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Documents existants
        </h3>
        {documents.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
            <p className="text-gray-500 text-sm">Aucun document disponible</p>
          </div>
        ) : (
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
        )}
      </div>
    </div>
  );
}
