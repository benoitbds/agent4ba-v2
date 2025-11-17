"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

interface ClarificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (response: string) => void;
  question: string;
}

export default function ClarificationModal({
  isOpen,
  onClose,
  onSubmit,
  question,
}: ClarificationModalProps) {
  const t = useTranslations();
  const [response, setResponse] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!response.trim()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(response.trim());
      // Réinitialiser le champ après soumission
      setResponse("");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setResponse("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">
            {t("clarification.title") || "L'agent a besoin d'une clarification"}
          </h2>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="flex flex-col">
          <div className="px-6 py-4 flex-1">
            {/* Question de l'agent */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t("clarification.question") || "Question"}
              </label>
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-gray-800">{question}</p>
              </div>
            </div>

            {/* Champ de réponse */}
            <div className="mb-4">
              <label htmlFor="clarification-response" className="block text-sm font-medium text-gray-700 mb-2">
                {t("clarification.yourResponse") || "Votre réponse"}
              </label>
              <textarea
                id="clarification-response"
                value={response}
                onChange={(e) => setResponse(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[150px]"
                placeholder={t("clarification.responsePlaceholder") || "Entrez votre réponse..."}
                autoFocus
                disabled={isSubmitting}
                required
              />
            </div>
          </div>

          {/* Footer Actions */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {t("clarification.cancel") || "Annuler"}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !response.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting
                ? (t("clarification.submitting") || "Envoi en cours...")
                : (t("clarification.submit") || "Soumettre la clarification")
              }
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
