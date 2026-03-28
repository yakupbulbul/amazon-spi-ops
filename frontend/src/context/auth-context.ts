import { createContext } from "react";

import type { AuthUser } from "../lib/api";

export type AuthContextValue = {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: AuthUser | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

