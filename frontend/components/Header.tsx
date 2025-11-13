"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Menu, X, Sparkles } from "lucide-react";
import { UserMenu } from "./UserMenu";
import { ProjectMenu } from "./ProjectMenu";
import ProjectSelector from "./ProjectSelector";

/**
 * Header - Main application header component
 * Displays app logo, project selector, project actions menu, and user menu
 * Responsive with hamburger menu for mobile devices
 */
interface HeaderProps {
  projects: string[];
  selectedProject: string;
  onProjectChange: (projectId: string) => void;
  onOpenDocuments: () => void;
  onCreateProject: () => void;
  onDeleteProject: () => void;
}

export function Header({
  projects,
  selectedProject,
  onProjectChange,
  onOpenDocuments,
  onCreateProject,
  onDeleteProject,
}: HeaderProps) {
  const router = useRouter();
  const t = useTranslations();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left: Logo and Title */}
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-3 hover:opacity-80 transition-opacity focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg"
          >
            <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg shadow-md">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 hidden sm:block">
              {t("header.title", { default: "Agent4BA" })}
            </h1>
          </button>

          {/* Center: Project Selector (Desktop) */}
          <div className="hidden md:flex items-center gap-3">
            <ProjectSelector
              projects={projects}
              selectedProject={selectedProject}
              onProjectChange={onProjectChange}
            />
          </div>

          {/* Right: Action Menus (Desktop) */}
          <div className="hidden md:flex items-center gap-3">
            <ProjectMenu
              selectedProject={selectedProject}
              onOpenDocuments={onOpenDocuments}
              onCreateProject={onCreateProject}
              onDeleteProject={onDeleteProject}
              disabled={!selectedProject}
            />
            <UserMenu />
          </div>

          {/* Mobile: Hamburger Button + User Menu */}
          <div className="flex md:hidden items-center gap-2">
            <UserMenu />
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label={isMobileMenuOpen ? "Fermer le menu" : "Ouvrir le menu"}
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 py-4 space-y-4">
            {/* Project Selector */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-2">
                {t("project.label", { default: "Projet" })}
              </h3>
              <ProjectSelector
                projects={projects}
                selectedProject={selectedProject}
                onProjectChange={onProjectChange}
              />
            </div>

            {/* Project Actions */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-2">
                {t("projectMenu.actions", { default: "Actions" })}
              </h3>
              <div className="space-y-1">
                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onOpenDocuments();
                  }}
                  disabled={!selectedProject}
                  className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>{t("documents.title", { default: "Documents" })}</span>
                </button>
                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onCreateProject();
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  <span>{t("project.newProject", { default: "Nouveau projet" })}</span>
                </button>
                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onDeleteProject();
                  }}
                  disabled={!selectedProject}
                  className="w-full flex items-center gap-3 px-4 py-3 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>{t("project.deleteProject", { default: "Supprimer" })}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
