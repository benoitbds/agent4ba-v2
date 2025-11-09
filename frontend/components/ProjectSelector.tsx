"use client";

interface ProjectSelectorProps {
  projects: string[];
  selectedProject: string;
  onProjectChange: (projectId: string) => void;
  onCreateProject?: () => void;
}

export default function ProjectSelector({
  projects,
  selectedProject,
  onProjectChange,
  onCreateProject,
}: ProjectSelectorProps) {
  return (
    <div className="flex items-center gap-3">
      <label htmlFor="project-select" className="text-sm font-medium text-gray-700">
        Projet :
      </label>
      <select
        id="project-select"
        value={selectedProject}
        onChange={(e) => onProjectChange(e.target.value)}
        className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
      >
        {projects.length === 0 ? (
          <option value="">Aucun projet disponible</option>
        ) : (
          projects.map((project) => (
            <option key={project} value={project}>
              {project}
            </option>
          ))
        )}
      </select>
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
