/**
 * Hook React pour gérer les utilisateurs d'un projet
 * Permet de récupérer, ajouter et supprimer des utilisateurs
 */

import { useState, useEffect, useCallback } from 'react';

interface User {
  id: string;
  username: string;
}

interface UseProjectUsersReturn {
  users: User[];
  isLoading: boolean;
  error: string | null;
  mutate: () => Promise<void>;
}

/**
 * Fonction utilitaire pour construire l'URL de l'API
 */
function getApiUrl(path: string): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Supprimer le slash final de la base si présent
  const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;

  // S'assurer que le chemin commence par un slash
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  return `${cleanBase}${cleanPath}`;
}

/**
 * Hook personnalisé pour gérer les utilisateurs d'un projet
 *
 * @param projectId - L'ID du projet
 * @returns Un objet contenant les utilisateurs, l'état de chargement, l'erreur et une fonction mutate
 *
 * @example
 * const { users, isLoading, error, mutate } = useProjectUsers(projectId);
 */
export function useProjectUsers(projectId: string | null): UseProjectUsersReturn {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    if (!projectId) {
      setUsers([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');

      if (!token) {
        throw new Error('No authentication token found');
      }

      const url = getApiUrl(`/projects/${projectId}/users`);
      console.log(`[USE_PROJECT_USERS] Fetching users for project: ${projectId}`);
      console.log(`[USE_PROJECT_USERS] API URL: ${url}`);

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch users' }));
        throw new Error(errorData.detail || `HTTP ${response.status}: Failed to fetch users`);
      }

      const data: User[] = await response.json();
      console.log(`[USE_PROJECT_USERS] Successfully fetched ${data.length} users`);
      setUsers(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('[USE_PROJECT_USERS] Error fetching users:', errorMessage);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  // Fonction mutate pour rafraîchir manuellement la liste
  const mutate = useCallback(async () => {
    await fetchUsers();
  }, [fetchUsers]);

  // Charger les utilisateurs au montage et quand le projectId change
  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  return {
    users,
    isLoading,
    error,
    mutate,
  };
}
