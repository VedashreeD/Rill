import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { api } from "../api/client";
import type { UserPublic } from "../types";

interface AuthContextValue {
  user: UserPublic | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(() => {
    const raw = localStorage.getItem("rill_user");
    return raw ? (JSON.parse(raw) as UserPublic) : null;
  });
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem("rill_token");
    localStorage.removeItem("rill_user");
    setUser(null);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("rill_token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    api
      .me()
      .then((meData) => {
        const publicUser: UserPublic = { id: meData.id, username: meData.username };
        localStorage.setItem("rill_user", JSON.stringify(publicUser));
        setUser(publicUser);
      })
      .catch(() => {
        logout();
      })
      .finally(() => {
        setLoading(false);
      });
  }, [logout]);

  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener("unauthorized", handleUnauthorized);
    return () => window.removeEventListener("unauthorized", handleUnauthorized);
  }, [logout]);

  const login = useCallback(async (username: string, password: string) => {
    const { token, user } = await api.login(username, password);
    localStorage.setItem("rill_token", token);
    localStorage.setItem("rill_user", JSON.stringify(user));
    setUser(user);
  }, []);

  const register = useCallback(async (username: string, password: string) => {
    const { token, user } = await api.register(username, password);
    localStorage.setItem("rill_token", token);
    localStorage.setItem("rill_user", JSON.stringify(user));
    setUser(user);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
