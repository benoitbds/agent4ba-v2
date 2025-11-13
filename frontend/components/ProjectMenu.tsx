"use client";

import { useState, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import { FileText, Plus, Trash2, Settings } from "lucide-react";

/**
 * ProjectMenu - Dropdown menu for project-related actions
 * Groups project actions: view documents, create project, delete project
 */
interface ProjectMenuProps {
  selectedProject: string;
  onOpenDocuments: () => void;
  onCreateProject: () => void;
  onDeleteProject: () => void;
  disabled?: boolean;
}

export function ProjectMenu({
  selectedProject,
  onOpenDocuments,
  onCreateProject,
  onDeleteProject,
  disabled = false,
}: ProjectMenuProps) {
  const t = useTranslations();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  return (
    <div className="relative" ref={menuRef}>
      {/* Project Actions Button - Settings Icon */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="flex items-center justify-center w-10 h-10 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white disabled:hover:border-gray-300"
        aria-expanded={isOpen}
        aria-haspopup="true"
        title={t("projectMenu.actions", { default: "Actions projet" })}
      >
        <Settings className="w-5 h-5" />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
          {/* Documents */}
          <button
            onClick={() => {
              setIsOpen(false);
              onOpenDocuments();
            }}
            disabled={!selectedProject}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors focus:outline-none focus:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white"
          >
            <FileText className="w-4 h-4" />
            <span>{t("documents.title", { default: "Documents du projet" })}</span>
          </button>

          <div className="border-t border-gray-100 my-1" />

          {/* New Project */}
          <button
            onClick={() => {
              setIsOpen(false);
              onCreateProject();
            }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-blue-600 hover:bg-blue-50 transition-colors focus:outline-none focus:bg-blue-50"
          >
            <Plus className="w-4 h-4" />
            <span>{t("project.newProject", { default: "Nouveau projet" })}</span>
          </button>

          {/* Delete Project */}
          <button
            onClick={() => {
              setIsOpen(false);
              onDeleteProject();
            }}
            disabled={!selectedProject}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors focus:outline-none focus:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white"
          >
            <Trash2 className="w-4 h-4" />
            <span>{t("project.deleteProject", { default: "Supprimer le projet" })}</span>
          </button>
        </div>
      )}
    </div>
  );
}
