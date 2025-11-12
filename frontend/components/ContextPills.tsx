"use client";

import { X, FileText, ListTodo } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ContextItem } from "@/types/events";

interface ContextPillsProps {
  context: ContextItem[];
  onRemove: (id: string) => void;
}

export default function ContextPills({ context, onRemove }: ContextPillsProps) {
  const t = useTranslations();

  if (context.length === 0) {
    return null;
  }

  return (
    <div className="mt-3">
      <p className="text-xs text-gray-600 mb-2">{t("context.selectedItems")}</p>
      <div className="flex flex-wrap gap-2">
        {context.map((item) => (
          <div
            key={`${item.type}-${item.id}`}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              item.type === "document"
                ? "bg-red-100 text-red-800 border border-red-200"
                : "bg-blue-100 text-blue-800 border border-blue-200"
            }`}
          >
            {/* Icon based on type */}
            {item.type === "document" ? (
              <FileText className="w-4 h-4" />
            ) : (
              <ListTodo className="w-4 h-4" />
            )}

            {/* Item name */}
            <span className="max-w-xs truncate">{item.name}</span>

            {/* Remove button */}
            <button
              onClick={() => onRemove(item.id)}
              className="ml-1 hover:bg-white hover:bg-opacity-50 rounded-full p-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-gray-400"
              title={t("context.remove")}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
