"use client";

import { useState } from "react";
import { useTranslations } from 'next-intl';

interface ChatInputProps {
  onSubmit: (query: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({ onSubmit, disabled = false, placeholder }: ChatInputProps) {
  const t = useTranslations();
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !disabled) {
      onSubmit(query);
      setQuery("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder || t('newRequest.placeholder')}
          disabled={disabled}
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={disabled || !query.trim()}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {t('newRequest.send')}
        </button>
      </div>

      <p className="mt-2 text-sm text-gray-500">
        {t('newRequest.hint')}
      </p>
    </form>
  );
}
