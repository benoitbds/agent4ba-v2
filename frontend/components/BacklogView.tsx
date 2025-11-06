"use client";

import type { WorkItem } from "@/types/events";

interface BacklogViewProps {
  items: WorkItem[];
}

export default function BacklogView({ items }: BacklogViewProps) {
  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <div className="text-center">
          <p className="text-lg">Aucun item dans le backlog</p>
          <p className="text-sm mt-2">
            Soumettez une requête pour commencer à construire votre backlog
          </p>
        </div>
      </div>
    );
  }

  // Organize items by hierarchy (features at top, then their children)
  const features = items.filter((item) => item.type === "feature");
  const childItems = items.filter((item) => item.type !== "feature");

  const renderWorkItem = (item: WorkItem, isChild: boolean = false) => (
    <div
      key={item.id}
      className={`p-4 bg-gray-50 rounded-lg border border-gray-200 ${
        isChild ? "ml-6" : ""
      }`}
    >
      <div className="flex items-start gap-2">
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
          <h4 className="font-semibold text-gray-900">{item.title}</h4>
          <p className="text-sm text-gray-600 mt-1">{item.description}</p>
          {item.attributes && (
            <div className="flex gap-2 mt-2 text-xs flex-wrap">
              {item.attributes.priority && (
                <span className="px-2 py-1 bg-gray-200 rounded">
                  Priorité: {item.attributes.priority}
                </span>
              )}
              {item.attributes.points !== undefined && (
                <span className="px-2 py-1 bg-gray-200 rounded">
                  Points: {item.attributes.points}
                </span>
              )}
              {item.attributes.status && (
                <span className="px-2 py-1 bg-gray-200 rounded">
                  Statut: {item.attributes.status}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Backlog du projet</h2>
        <span className="text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded-full">
          {items.length} item{items.length > 1 ? "s" : ""}
        </span>
      </div>

      <div className="space-y-4">
        {/* Features with their children */}
        {features.map((feature) => {
          const children = childItems.filter(
            (item) => item.parent_id === feature.id
          );
          return (
            <div key={feature.id} className="space-y-2">
              {renderWorkItem(feature)}
              {children.map((child) => renderWorkItem(child, true))}
            </div>
          );
        })}

        {/* Orphan items (no parent) */}
        {childItems
          .filter((item) => !item.parent_id)
          .map((item) => renderWorkItem(item))}
      </div>
    </div>
  );
}
