"use client";

import { useTranslations } from "next-intl";

/**
 * ProjectSelector - Simple dropdown for project selection
 * Actions (new/delete) are now in ProjectMenu
 */
interface ProjectSelectorProps {
  projects: string[];
  selectedProject: string;
  onProjectChange: (projectId: string) => void;
}

export default function ProjectSelector({
  projects,
  selectedProject,
  onProjectChange,
}: ProjectSelectorProps) {
  const t = useTranslations();

  return (
    <div className="flex items-center gap-3">
      <label
        htmlFor="project-select"
        className="text-sm font-semibold text-gray-900 dark:text-gray-100"
      >
        {t("project.label")}
      </label>
      <select
        id="project-select"
        value={selectedProject}
        onChange={(e) => onProjectChange(e.target.value)}
        className="px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg
                   bg-white dark:bg-gray-800
                   text-gray-900 dark:text-gray-100
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                   hover:border-gray-400 dark:hover:border-gray-500
                   transition-colors duration-200
                   shadow-sm"
      >
        {projects.length === 0 ? (
          <option value="" className="text-gray-900 dark:text-gray-100">
            {t("project.noProjects")}
          </option>
        ) : (
          projects.map((project) => (
            <option
              key={project}
              value={project}
              className="text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800"
            >
              {project}
            </option>
          ))
        )}
      </select>
    </div>
  );
}
