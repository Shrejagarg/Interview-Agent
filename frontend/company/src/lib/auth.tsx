"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import * as api from "./api";

interface User {
  user_id: string;
  email: string;
  role: string;
  full_name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

function setCookie(name: string, value: string, days: number) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function removeCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("auth_token");
    if (saved) {
      setToken(saved);
      api
        .getMe()
        .then((u) => setUser(u))
        .catch(() => {
          localStorage.removeItem("auth_token");
          removeCookie("auth_token");
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const loginFn = async (email: string, password: string) => {
    const res = await api.login(email, password);
    localStorage.setItem("auth_token", res.access_token);
    setCookie("auth_token", res.access_token, 7);
    setToken(res.access_token);
    setUser({ user_id: res.user_id, email: res.email, role: res.role });
  };

  const registerFn = async (email: string, password: string, fullName?: string) => {
    const res = await api.register(email, password, fullName);
    localStorage.setItem("auth_token", res.access_token);
    setCookie("auth_token", res.access_token, 7);
    setToken(res.access_token);
    setUser({ user_id: res.user_id, email: res.email, role: res.role });
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    removeCookie("auth_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login: loginFn, register: registerFn, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
