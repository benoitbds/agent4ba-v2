"use client";

import { useState, useRef } from "react";

interface UploadDocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  onUploadSuccess: () => void;
}

export default function UploadDocumentModal({
  isOpen,
  onClose,
  projectId,
  onUploadSuccess,
}: UploadDocumentModalProps) {
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

      // Close modal after a short delay to show success message
      setTimeout(() => {
        handleClose();
      }, 1500);
    } catch (error) {
      setUploadStatus("error");
      setStatusMessage(
        error instanceof Error
          ? error.message
          : "Erreur lors de l'upload du fichier"
      );
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setUploadStatus("idle");
    setStatusMessage("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">
          Uploader un document
        </h2>

        <div className="space-y-4">
          <div>
            <label htmlFor="file-input" className="block text-sm font-medium text-gray-700 mb-2">
              Sélectionner un fichier PDF
            </label>
            <input
              id="file-input"
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
            <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded border border-gray-200">
              Fichier sélectionné: <strong>{selectedFile.name}</strong> (
              {(selectedFile.size / 1024).toFixed(2)} KB)
            </div>
          )}

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

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={uploadStatus === "uploading"}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Annuler
            </button>
            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploadStatus === "uploading"}
              className={`px-4 py-2 rounded-lg font-semibold text-white transition-colors ${
                !selectedFile || uploadStatus === "uploading"
                  ? "bg-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              {uploadStatus === "uploading" ? "Upload en cours..." : "Uploader"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
