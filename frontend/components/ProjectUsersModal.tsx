"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { X, UserPlus, Trash2, Loader2 } from "lucide-react";
import { useProjectUsers } from "@/hooks/useProjectUsers";
import { useAuth } from "@/context/AuthContext";

interface SearchUser {
  id: string;
  username: string;
}

interface ProjectUsersModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
}

export function ProjectUsersModal({ isOpen, onClose, projectId }: ProjectUsersModalProps) {
  const t = useTranslations();
  const { token } = useAuth();
  const { users, isLoading, error, mutate } = useProjectUsers(isOpen ? projectId : null, token);
  const [newUsername, setNewUsername] = useState("");
  const [addingUser, setAddingUser] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Autocomplete states
  const [searchResults, setSearchResults] = useState<SearchUser[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedUser, setSelectedUser] = useState<SearchUser | null>(null);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fonction de recherche d'utilisateurs
  const searchUsers = useCallback(async (query: string) => {
    if (!query.trim() || query.length < 1) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    setIsSearching(true);
    try {
      if (!token) {
        throw new Error("No authentication token found");
      }

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url = `${baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl}/users/search?query=${encodeURIComponent(query)}`;

      const response = await fetch(url, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to search users");
      }

      const results: SearchUser[] = await response.json();
      setSearchResults(results);
      setShowDropdown(results.length > 0);
    } catch (err) {
      console.error("Error searching users:", err);
      setSearchResults([]);
      setShowDropdown(false);
    } finally {
      setIsSearching(false);
    }
  }, [token]);

  // Debounce pour la recherche
  useEffect(() => {
    const timer = setTimeout(() => {
      if (newUsername && !selectedUser) {
        searchUsers(newUsername);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [newUsername, selectedUser, searchUsers]);

  // Fermer le dropdown si on clique en dehors
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Gérer la sélection d'un utilisateur
  const handleSelectUser = (user: SearchUser) => {
    setSelectedUser(user);
    setNewUsername(user.username);
    setShowDropdown(false);
    setSearchResults([]);
    setHighlightedIndex(-1);
  };

  // Gérer les touches clavier pour la navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showDropdown || searchResults.length === 0) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < searchResults.length - 1 ? prev + 1 : prev
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
      case "Enter":
        e.preventDefault();
        if (highlightedIndex >= 0 && highlightedIndex < searchResults.length) {
          handleSelectUser(searchResults[highlightedIndex]);
        } else if (searchResults.length === 1) {
          handleSelectUser(searchResults[0]);
        }
        break;
      case "Escape":
        setShowDropdown(false);
        setHighlightedIndex(-1);
        break;
    }
  };

  const handleAddUser = async () => {
    if (!newUsername.trim()) return;

    setAddingUser(true);
    setActionError(null);

    try {
      if (!token) {
        throw new Error("No authentication token found");
      }

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
      setSelectedUser(null);
      setSearchResults([]);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setAddingUser(false);
    }
  };

  const handleRemoveUser = async (userId: string) => {
    setActionError(null);

    try {
      if (!token) {
        throw new Error("No authentication token found");
      }

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
              <div className="flex-1 relative" ref={dropdownRef}>
                <input
                  ref={inputRef}
                  type="text"
                  value={newUsername}
                  onChange={(e) => {
                    setNewUsername(e.target.value);
                    setSelectedUser(null);
                  }}
                  onKeyDown={handleKeyDown}
                  onFocus={() => {
                    if (searchResults.length > 0) {
                      setShowDropdown(true);
                    }
                  }}
                  placeholder={t("users.usernamePlaceholder", { default: "Nom d'utilisateur" })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoComplete="off"
                />
                {isSearching && (
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                    <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
                  </div>
                )}

                {/* Dropdown de suggestions */}
                {showDropdown && searchResults.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {searchResults.map((user, index) => (
                      <button
                        key={user.id}
                        type="button"
                        onClick={() => handleSelectUser(user)}
                        className={`w-full text-left px-4 py-2 hover:bg-blue-50 transition-colors ${
                          index === highlightedIndex ? "bg-blue-100" : ""
                        } ${index === 0 ? "rounded-t-lg" : ""} ${
                          index === searchResults.length - 1 ? "rounded-b-lg" : ""
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-medium">
                            {user.username.charAt(0).toUpperCase()}
                          </div>
                          <span className="text-gray-900">{user.username}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={handleAddUser}
                disabled={addingUser || !selectedUser}
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
