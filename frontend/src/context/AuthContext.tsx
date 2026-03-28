import {
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getCurrentUser, login as loginRequest, type AuthUser } from "../lib/api";
import { AuthContext, type AuthContextValue } from "./auth-context";

const ACCESS_TOKEN_STORAGE_KEY = "amazon-seller-ops.access-token";

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (!token) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser(token);
        if (!cancelled) {
          setUser(currentUser);
        }
      } catch {
        if (!cancelled) {
          localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void restoreSession();

    return () => {
      cancelled = true;
    };
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: Boolean(token && user),
      isLoading,
      user,
      token,
      async login(email: string, password: string) {
        const response = await loginRequest(email, password);
        localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, response.access_token);
        setToken(response.access_token);
        setUser(response.user);
        setIsLoading(false);
      },
      logout() {
        localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
        setToken(null);
        setUser(null);
        setIsLoading(false);
      },
    }),
    [isLoading, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
