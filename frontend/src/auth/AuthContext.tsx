import {
  createContext,
  useContext,
  useMemo,
  useState,
} from "react";

import { login as loginRequest, register as registerRequest } from "../api/authApi";
import { tokenStorage } from "./tokenStorage";

import type { LoginRequest, RegisterRequest } from "../types/auth";
import type { ReactNode } from "react";

interface AuthContextValue {
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (request: LoginRequest) => Promise<void>;
  register: (request: RegisterRequest) => Promise<string>;
  authenticate: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({
  children,
}: AuthProviderProps) {
  const [accessToken, setAccessToken] = useState<string | null>(
    () => tokenStorage.get(),
  );

  function authenticate(token: string): void {
    tokenStorage.set(token);
    setAccessToken(token);
  }

  async function login(request: LoginRequest): Promise<void> {
    const response = await loginRequest(request);
    authenticate(response.access_token);
  }

  // Sign-up no longer signs you in: the address must be verified first.
  async function register(request: RegisterRequest): Promise<string> {
    const response = await registerRequest(request);
    return response.message;
  }

  function logout(): void {
    tokenStorage.remove();
    setAccessToken(null);
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken,
      isAuthenticated: Boolean(accessToken),
      login,
      register,
      authenticate,
      logout,
    }),
    [accessToken],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider",
    );
  }

  return context;
}
