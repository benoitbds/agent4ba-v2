"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "@/context/AuthContext";
import Link from "next/link";

export default function RegisterPage() {
  const t = useTranslations();
  const router = useRouter();
  const { register, isAuthenticated } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  // Redirect if already authenticated
  if (isAuthenticated) {
    router.push("/");
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    // Validate password match
    if (password !== confirmPassword) {
      setError(t("auth.register.passwordMismatch", { default: "Passwords do not match" }));
      setIsLoading(false);
      return;
    }

    // Validate password length
    if (password.length < 6) {
      setError(t("auth.register.passwordTooShort", { default: "Password must be at least 6 characters" }));
      setIsLoading(false);
      return;
    }

    // Validate username length
    if (username.length < 3) {
      setError(t("auth.register.usernameTooShort", { default: "Username must be at least 3 characters" }));
      setIsLoading(false);
      return;
    }

    try {
      await register(username, password);
      setSuccess(true);
      // Redirect to login page after 2 seconds
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-center text-4xl font-bold text-gray-900">
            Agent4BA
          </h1>
          <h2 className="mt-6 text-center text-3xl font-semibold text-gray-800">
            {t("auth.register.title", { default: "Create your account" })}
          </h2>
        </div>

        {/* Success Message */}
        {success ? (
          <div className="bg-green-100 border border-green-300 text-green-800 px-4 py-3 rounded-lg">
            <p className="text-sm font-semibold text-center">
              {t("auth.register.success", { default: "Account created successfully! Redirecting to login..." })}
            </p>
          </div>
        ) : (
          // Register Form
          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            <div className="rounded-md shadow-sm space-y-4">
              {/* Username Input */}
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                  {t("auth.register.username", { default: "Username" })}
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  placeholder={t("auth.register.usernamePlaceholder", { default: "Choose a username (min. 3 characters)" })}
                />
              </div>

              {/* Password Input */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  {t("auth.register.password", { default: "Password" })}
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  placeholder={t("auth.register.passwordPlaceholder", { default: "Choose a password (min. 6 characters)" })}
                />
              </div>

              {/* Confirm Password Input */}
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
                  {t("auth.register.confirmPassword", { default: "Confirm Password" })}
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  placeholder={t("auth.register.confirmPasswordPlaceholder", { default: "Confirm your password" })}
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-100 border border-red-300 text-red-800 px-4 py-3 rounded-lg">
                <p className="text-sm font-semibold">{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                    {t("auth.register.creating", { default: "Creating account..." })}
                  </span>
                ) : (
                  t("auth.register.signUp", { default: "Sign up" })
                )}
              </button>
            </div>

            {/* Login Link */}
            <div className="text-center">
              <p className="text-sm text-gray-600">
                {t("auth.register.hasAccount", { default: "Already have an account?" })}{" "}
                <Link href="/login" className="font-medium text-blue-600 hover:text-blue-500">
                  {t("auth.register.loginLink", { default: "Sign in" })}
                </Link>
              </p>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
