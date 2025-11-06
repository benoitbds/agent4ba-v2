"use client";

import { useState } from "react";

interface ChatInputProps {
  onSubmit: (query: string, documentContent?: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSubmit, disabled = false }: ChatInputProps) {
  const [query, setQuery] = useState("");
  const [documentContent, setDocumentContent] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !disabled) {
      onSubmit(query, documentContent.trim() || undefined);
      setQuery("");
      setDocumentContent("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Décrivez votre besoin (ex: Crée le backlog à partir de ce texte)"
            disabled={disabled}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={disabled || !query.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            Envoyer
          </button>
        </div>

        <div>
          <label htmlFor="documentContent" className="block text-sm font-medium text-gray-700 mb-1">
            Document à analyser (optionnel)
          </label>
          <textarea
            id="documentContent"
            value={documentContent}
            onChange={(e) => setDocumentContent(e.target.value)}
            placeholder="Collez ici le texte du document à analyser (ex: email, extrait de cahier des charges...)"
            disabled={disabled}
            rows={5}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed resize-y"
          />
        </div>
      </div>

      <p className="mt-2 text-sm text-gray-500">
        L&apos;agent analysera votre demande et proposera des modifications au backlog
      </p>
    </form>
  );
}
