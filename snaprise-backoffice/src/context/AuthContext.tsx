"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useCallback,
} from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import type { AdminUser } from "@/types/api/admin.types";

interface AuthContextType {
  token: string | null;
  user: AdminUser | null;
  /** Reason the last sign-in attempt was refused (e.g. not a superuser). */
  authError: string | null;
  login: (accessToken: string, refreshToken?: string) => void;
  logout: () => void;
  isLoading: boolean;
}

const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";
// Refresh this many ms before the access token's exp so a request never races expiry.
const REFRESH_SKEW_MS = 60_000;
const NOT_ADMIN_MESSAGE =
  "Admins only — this account doesn't have backoffice access.";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/** Decode a JWT payload and return its `exp` (seconds since epoch), or null. */
function getTokenExp(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.exp === "number" ? json.exp : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AdminUser | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Timer handle for the next proactive refresh; cleared on logout/unmount.
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimer.current) {
      clearTimeout(refreshTimer.current);
      refreshTimer.current = null;
    }
  }, []);

  // Drop all session state. Used by logout and by the superuser gate when it
  // refuses a non-admin account.
  const clearSession = useCallback(() => {
    clearRefreshTimer();
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setToken(null);
    setUser(null);
  }, [clearRefreshTimer]);

  const logout = useCallback(() => {
    clearSession();
    router.push("/login");
  }, [clearSession, router]);

  // Schedule a silent refresh shortly before the access token expires.
  const scheduleRefresh = useCallback(
    (accessToken: string) => {
      clearRefreshTimer();
      const exp = getTokenExp(accessToken);
      if (!exp) return;
      const delay = Math.max(exp * 1000 - Date.now() - REFRESH_SKEW_MS, 5_000);
      refreshTimer.current = setTimeout(() => {
        void refreshAccessToken();
      }, delay);
    },
    [clearRefreshTimer]
  );

  // Exchange the stored refresh token for a fresh access token. Returns the new
  // access token, or null if refresh failed.
  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    if (!refreshToken) {
      logout();
      return null;
    }
    try {
      const res = await authApi.refresh(refreshToken);
      localStorage.setItem(ACCESS_KEY, res.access_token);
      if (res.refresh_token) localStorage.setItem(REFRESH_KEY, res.refresh_token);
      setToken(res.access_token);
      scheduleRefresh(res.access_token);
      return res.access_token;
    } catch (error) {
      console.error("Token refresh failed:", error);
      logout();
      return null;
    }
  }, [logout, scheduleRefresh]);

  // Resolve the user behind a token and enforce the superuser gate. On success
  // the session is established (and optionally redirected to /leads); on a
  // non-superuser account the session is cleared and authError is set.
  const establishSession = useCallback(
    (authToken: string, userData: AdminUser, redirectOnSuccess: boolean): boolean => {
      if (!userData.is_superuser) {
        setAuthError(NOT_ADMIN_MESSAGE);
        clearSession();
        return false;
      }
      setAuthError(null);
      setToken(authToken);
      setUser(userData);
      scheduleRefresh(authToken);
      if (redirectOnSuccess) router.push("/leads");
      return true;
    },
    [clearSession, scheduleRefresh, router]
  );

  // Validate a token (on startup or right after login). Tries one refresh before
  // giving up so a returning admin with an expired access token stays in.
  const verifyToken = useCallback(
    async (authToken: string, redirectOnSuccess = false) => {
      try {
        const userData = (await authApi.me(authToken)) as AdminUser;
        establishSession(authToken, userData, redirectOnSuccess);
      } catch {
        const newToken = await refreshAccessToken();
        if (newToken) {
          try {
            const userData = (await authApi.me(newToken)) as AdminUser;
            establishSession(newToken, userData, redirectOnSuccess);
          } catch (e) {
            console.error("Verification after refresh failed:", e);
            clearSession();
          }
        }
      } finally {
        setIsLoading(false);
      }
    },
    [establishSession, refreshAccessToken, clearSession]
  );

  useEffect(() => {
    const savedToken = localStorage.getItem(ACCESS_KEY);
    if (savedToken) {
      verifyToken(savedToken);
    } else {
      setIsLoading(false);
    }
    return () => clearRefreshTimer();
    // Run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = (accessToken: string, refreshToken?: string) => {
    setAuthError(null);
    localStorage.setItem(ACCESS_KEY, accessToken);
    if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
    // Verify + enforce the superuser gate BEFORE redirecting, so a non-admin
    // never briefly lands on an admin page.
    verifyToken(accessToken, true);
  };

  return (
    <AuthContext.Provider value={{ token, user, authError, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
