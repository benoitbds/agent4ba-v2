"use client";

import { useTranslations } from "next-intl";
import { useAuth } from "@/context/AuthContext";
import { LogOut, User } from "lucide-react";

export function UserMenu() {
  const t = useTranslations();
  const { user, logout } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <div className="flex items-center gap-4">
      {/* User Info */}
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg">
        <User className="w-5 h-5 text-gray-600" />
        <span className="text-sm font-medium text-gray-700">{user.username}</span>
      </div>

      {/* Logout Button */}
      <button
        onClick={logout}
        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
        title={t("auth.logout", { default: "Logout" })}
      >
        <LogOut className="w-5 h-5" />
        <span className="font-medium">{t("auth.logout", { default: "Logout" })}</span>
      </button>
    </div>
  );
}
