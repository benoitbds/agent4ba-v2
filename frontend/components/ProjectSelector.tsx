"use client";

import { Trash2 } from "lucide-react";

interface ProjectSelectorProps {
  projects: string[];
  selectedProject: string;
  onProjectChange: (projectId: string) => void;
  onCreateProject?: () => void;
  onDeleteProject?: () => void;
}

export default function ProjectSelector({
  projects,
  selectedProject,
  onProjectChange,
  onCreateProject,
  onDeleteProject,
}: ProjectSelectorProps) {
  return (
    <div className="flex items-center gap-3">
      <label
        htmlFor="project-select"
        className="text-sm font-semibold text-gray-900 dark:text-gray-100"
      >
        Projet :
      </label>
      <select
        id="project-select"
        value={selectedProject}
        onChange={(e) => onProjectChange(e.target.value)}
        className="px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg
                   bg-white dark:bg-gray-800
                   text-gray-900 dark:text-gray-100
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500
                   hover:border-gray-400 dark:hover:border-gray-500
                   transition-colors duration-200
                   shadow-sm"
      >
        {projects.length === 0 ? (
          <option value="" className="text-gray-900 dark:text-gray-100">
            Aucun projet disponible
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
      {onDeleteProject && (
        <button
          onClick={onDeleteProject}
          disabled={!selectedProject || projects.length === 0}
          className="p-2 border-2 border-red-300 text-red-600 rounded-lg hover:bg-red-50 hover:border-red-400 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:border-red-300"
          title="Supprimer le projet sélectionné"
        >
          <Trash2 className="w-5 h-5" />
        </button>
      )}
      {onCreateProject && (
        <button
          onClick={onCreateProject}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          title="Créer un nouveau projet"
        >
          + Nouveau projet
        </button>
      )}
    </div>
  );
}
