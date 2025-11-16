"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { X } from "lucide-react";
import type { Diagram, WorkItem } from "@/types/events";
import MermaidDiagram from "./MermaidDiagram";

interface DiagramEditorModalProps {
  isOpen: boolean;
  diagram: Diagram;
  workItem: WorkItem;
  projectId: string;
  onClose: () => void;
  onSave: (updatedWorkItem: WorkItem) => Promise<void>;
}

/**
 * Modale d'édition de diagramme avec vue split-screen
 * Panneau gauche: éditeur de code
 * Panneau droit: rendu en temps réel
 */
export default function DiagramEditorModal({
  isOpen,
  diagram,
  workItem,
  projectId,
  onClose,
  onSave,
}: DiagramEditorModalProps) {
  const t = useTranslations();
  const [code, setCode] = useState(diagram.code);
  const [debouncedCode, setDebouncedCode] = useState(diagram.code);
  const [isSaving, setIsSaving] = useState(false);

  // Debounce pour mettre à jour le rendu (300ms de délai)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedCode(code);
    }, 300);

    return () => clearTimeout(timer);
  }, [code]);

  // Reset le code quand le diagramme change
  useEffect(() => {
    setCode(diagram.code);
    setDebouncedCode(diagram.code);
  }, [diagram.code]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Créer une copie du work item avec le diagramme mis à jour
      const updatedDiagrams = (workItem.diagrams || []).map((d) =>
        d.id === diagram.id ? { ...diagram, code } : d
      );

      const updatedWorkItem: WorkItem = {
        ...workItem,
        diagrams: updatedDiagrams,
      };

      await onSave(updatedWorkItem);
      onClose();
    } catch (error) {
      console.error("Error saving diagram:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = useCallback(() => {
    // Reset le code aux valeurs d'origine
    setCode(diagram.code);
    setDebouncedCode(diagram.code);
    onClose();
  }, [diagram.code, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              {t("diagram.editor.title")}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {diagram.title} - {workItem.title}
            </p>
          </div>
          <button
            onClick={handleCancel}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label={t("common.close")}
          >
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>

        {/* Split Screen Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Panel - Code Editor */}
          <div className="w-1/2 flex flex-col border-r border-gray-200">
            <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex-shrink-0">
              <h3 className="text-sm font-semibold text-gray-700">
                {t("diagram.editor.code")}
              </h3>
            </div>
            <div className="flex-1 overflow-hidden">
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full h-full p-4 font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                spellCheck={false}
                placeholder={t("diagram.editor.codePlaceholder")}
              />
            </div>
          </div>

          {/* Right Panel - Live Preview */}
          <div className="w-1/2 flex flex-col">
            <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex-shrink-0">
              <h3 className="text-sm font-semibold text-gray-700">
                {t("diagram.editor.preview")}
              </h3>
            </div>
            <div className="flex-1 overflow-auto p-4 bg-gray-50">
              {debouncedCode ? (
                <MermaidDiagram code={debouncedCode} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  {t("diagram.editor.emptyPreview")}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3 flex-shrink-0">
          <button
            onClick={handleCancel}
            disabled={isSaving}
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {t("common.cancel")}
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? t("common.saving") : t("common.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
