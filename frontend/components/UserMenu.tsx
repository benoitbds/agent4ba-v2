"use client";

import { useState, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/context/AuthContext";
import { LogOut, User, Settings } from "lucide-react";

/**
 * UserMenu - Dropdown menu for user actions
 * Displays user avatar/name and provides access to profile, settings, and logout
 */
export function UserMenu() {
  const t = useTranslations();
  const { user, logout } = useAuth();
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

  if (!user) {
    return null;
  }

  return (
    <div className="relative" ref={menuRef}>
      {/* User Avatar Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-center w-10 h-10 bg-blue-600 hover:bg-blue-700 text-white rounded-full font-semibold text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        aria-expanded={isOpen}
        aria-haspopup="true"
        title={user.username}
      >
        {user.username.charAt(0).toUpperCase()}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
          {/* User Info Header */}
          <div className="px-4 py-3 border-b border-gray-100">
            <p className="text-sm font-semibold text-gray-900">{user.username}</p>
            <p className="text-xs text-gray-500 mt-1">{user.id}</p>
          </div>

          {/* Menu Items */}
          <button
            onClick={() => {
              setIsOpen(false);
              // TODO: Navigate to profile page
              console.log("Navigate to profile");
            }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors focus:outline-none focus:bg-gray-50"
          >
            <User className="w-4 h-4" />
            <span>{t("userMenu.profile", { default: "Profil" })}</span>
          </button>

          <button
            onClick={() => {
              setIsOpen(false);
              // TODO: Navigate to settings page
              console.log("Navigate to settings");
            }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors focus:outline-none focus:bg-gray-50"
          >
            <Settings className="w-4 h-4" />
            <span>{t("userMenu.settings", { default: "Paramètres" })}</span>
          </button>

          <div className="border-t border-gray-100 my-1" />

          <button
            onClick={() => {
              setIsOpen(false);
              logout();
            }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors focus:outline-none focus:bg-red-50"
          >
            <LogOut className="w-4 h-4" />
            <span>{t("auth.logout", { default: "Déconnexion" })}</span>
          </button>
        </div>
      )}
    </div>
  );
}
