"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { X, UserPlus, Trash2, Loader2 } from "lucide-react";
import { useProjectUsers } from "@/hooks/useProjectUsers";

interface ProjectUsersModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
}

export function ProjectUsersModal({ isOpen, onClose, projectId }: ProjectUsersModalProps) {
  const t = useTranslations();
  const { users, isLoading, error, mutate } = useProjectUsers(isOpen ? projectId : null);
  const [newUsername, setNewUsername] = useState("");
  const [addingUser, setAddingUser] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleAddUser = async () => {
    if (!newUsername.trim()) return;

    setAddingUser(true);
    setActionError(null);

    try {
      const token = localStorage.getItem("token");
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url = `${baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl}/projects/${projectId}/users`;

      const response = await fetch(url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username: newUsername }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to add user" }));
        throw new Error(errorData.detail || "Failed to add user");
      }

      // Refresh the users list
      await mutate();
      setNewUsername("");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setAddingUser(false);
    }
  };

  const handleRemoveUser = async (userId: string) => {
    setActionError(null);

    try {
      const token = localStorage.getItem("token");
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url = `${baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl}/projects/${projectId}/users/${userId}`;

      const response = await fetch(url, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to remove user" }));
        throw new Error(errorData.detail || "Failed to remove user");
      }

      // Refresh the users list
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unknown error");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {t("users.modalTitle", { default: "Utilisateurs du projet" })}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label={t("common.close", { default: "Fermer" })}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Error Message */}
          {(error || actionError) && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {error || actionError}
            </div>
          )}

          {/* Add User Section */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              {t("users.addUser", { default: "Ajouter un utilisateur" })}
            </h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                placeholder={t("users.usernamePlaceholder", { default: "Nom d'utilisateur" })}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyPress={(e) => {
                  if (e.key === "Enter") handleAddUser();
                }}
              />
              <button
                onClick={handleAddUser}
                disabled={addingUser || !newUsername.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {addingUser ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <UserPlus className="w-4 h-4" />
                )}
                {t("users.invite", { default: "Inviter" })}
              </button>
            </div>
          </div>

          {/* Users List */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              {t("users.currentUsers", { default: "Utilisateurs actuels" })}
            </h3>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
              </div>
            ) : users.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                {t("users.noUsers", { default: "Aucun utilisateur" })}
              </p>
            ) : (
              <div className="space-y-2">
                {users.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="text-gray-900">{user.username}</span>
                    <button
                      onClick={() => handleRemoveUser(user.id)}
                      className="text-red-600 hover:text-red-700 transition-colors p-1"
                      title={t("users.removeUser", { default: "Retirer l'utilisateur" })}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            {t("common.close", { default: "Fermer" })}
          </button>
        </div>
      </div>
    </div>
  );
}
