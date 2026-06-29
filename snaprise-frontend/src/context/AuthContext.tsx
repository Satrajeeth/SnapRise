"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useCallback,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { authApi } from "@/lib/api";

interface AuthContextType {
  token: string | null;
  user: any | null;
  login: (accessToken: string, refreshToken?: string) => void;
  logout: () => void;
  isLoading: boolean;
}

const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";
// Refresh this many ms before the access token's exp so a request never races
// expiry.
const REFRESH_SKEW_MS = 60_000;

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/** Decode a JWT payload and return its `exp` (seconds since epoch), or null. */
function getTokenExp(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    const json = JSON.parse(
      atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
    );
    return typeof json.exp === "number" ? json.exp : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // Timer handle for the next proactive refresh; cleared on logout/unmount.
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimer.current) {
      clearTimeout(refreshTimer.current);
      refreshTimer.current = null;
    }
  }, []);

  const logout = useCallback(() => {
    clearRefreshTimer();
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setToken(null);
    setUser(null);
    if (pathname?.startsWith("/dashboard")) {
      router.push("/login");
    }
  }, [clearRefreshTimer, pathname, router]);

  // Schedule a silent refresh shortly before the access token expires so an
  // open tab stays authenticated without the user noticing.
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

  // Exchange the stored refresh token for a fresh access (+ rotated refresh)
  // token. Returns the new access token, or null if refresh failed.
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

  // Validate a token on startup. If it's rejected, try one refresh before
  // giving up so a returning user with an expired access token stays logged in.
  const verifyToken = useCallback(
    async (authToken: string) => {
      try {
        const userData = await authApi.me(authToken);
        setToken(authToken);
        setUser(userData);
        scheduleRefresh(authToken);
      } catch (error) {
        const newToken = await refreshAccessToken();
        if (newToken) {
          try {
            setUser(await authApi.me(newToken));
          } catch (e) {
            console.error("Verification after refresh failed:", e);
            logout();
          }
        }
      } finally {
        setIsLoading(false);
      }
    },
    [logout, refreshAccessToken, scheduleRefresh]
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
    localStorage.setItem(ACCESS_KEY, accessToken);
    if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
    setToken(accessToken);
    scheduleRefresh(accessToken);
    verifyToken(accessToken);
    router.push("/dashboard");
  };

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isLoading }}>
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
