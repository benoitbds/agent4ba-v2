"use client";

import type { WorkItem } from "@/types/events";

interface BacklogViewProps {
  items: WorkItem[];
}

export default function BacklogView({ items }: BacklogViewProps) {
  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Aucun item dans le backlog</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold mb-4">Backlog du projet</h2>
      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="p-4 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
          >
            <div className="flex items-start gap-3">
              <span
                className={`px-2 py-1 text-xs font-semibold rounded ${
                  item.type === "feature"
                    ? "bg-purple-200 text-purple-800"
                    : item.type === "user_story"
                    ? "bg-blue-200 text-blue-800"
                    : "bg-green-200 text-green-800"
                }`}
              >
                {item.type}
              </span>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-gray-900">{item.title}</h3>
                  <span className="text-xs text-gray-500 font-mono">
                    {item.id}
                  </span>
                </div>
                {item.description && (
                  <p className="text-sm text-gray-600 mt-1">
                    {item.description}
                  </p>
                )}
                {item.attributes && (
                  <div className="flex gap-2 mt-2 text-xs">
                    {item.attributes.priority && (
                      <span className="px-2 py-1 bg-gray-100 rounded">
                        Priorité: {item.attributes.priority}
                      </span>
                    )}
                    {item.attributes.points !== undefined && (
                      <span className="px-2 py-1 bg-gray-100 rounded">
                        Points: {item.attributes.points}
                      </span>
                    )}
                    {item.attributes.status && (
                      <span className="px-2 py-1 bg-gray-100 rounded">
                        Statut: {item.attributes.status}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
