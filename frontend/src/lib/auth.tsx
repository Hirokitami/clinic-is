"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";
import type { Role, User } from "./types";

type AuthState = { user: User | null; loading: boolean; logout: () => Promise<void> };

const AuthContext = createContext<AuthState>({ user: null, loading: true, logout: async () => {} });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const logout = useCallback(async () => {
    await api.post("/auth/logout").catch(() => {});
    location.href = "/login";
  }, []);

  return <AuthContext.Provider value={{ user, loading, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function hasRole(user: User | null, roles: Role[]) {
  return !!user && roles.includes(user.role_code);
}
