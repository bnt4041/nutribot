import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  ReactNode,
} from "react";
import { api } from "../api/client";
import { tokens } from "../api/tokens";

interface AuthState {
  isAuthenticated: boolean;
  login: (code: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setAuthenticated] = useState<boolean>(
    () => !!tokens.getAccess(),
  );

  const login = useCallback(async (code: string) => {
    const { data } = await api.post("/auth/login", { code });
    tokens.set(data.access_token, data.refresh_token);
    setAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    tokens.clear();
    setAuthenticated(false);
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, login, logout }),
    [isAuthenticated, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
