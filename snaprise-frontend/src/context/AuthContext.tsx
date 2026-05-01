"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { authApi } from "@/lib/api";

interface AuthContextType {
  token: string | null;
  user: any | null;
  login: (token: string) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const savedToken = localStorage.getItem("access_token");
    if (savedToken) {
      verifyToken(savedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const verifyToken = async (authToken: string) => {
    try {
      const userData = await authApi.me(authToken);
      setToken(authToken);
      setUser(userData);
    } catch (error) {
      console.error("Token verification failed:", error);
      logout();
    } finally {
      setIsLoading(false);
    }
  };

  const login = (authToken: string) => {
    localStorage.setItem("access_token", authToken);
    setToken(authToken);
    verifyToken(authToken);
    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
    setUser(null);
    if (pathname === "/dashboard") {
      router.push("/login");
    }
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
