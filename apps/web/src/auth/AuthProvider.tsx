import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, api, messageForError } from "../api/client";
import type {
  CandidateRegistrationInput,
  LoginInput,
  Role,
  User,
} from "../types/domain";
import { AuthContext, type AuthContextValue } from "./context";

export function homeForRole(role: Role): string {
  return role === "candidate" ? "/candidate" : "/employer";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setSessionError(null);
    try {
      setUser(await api.me());
    } catch (error: unknown) {
      setUser(null);
      if (!(error instanceof ApiError && error.status === 401)) {
        setSessionError(messageForError(error));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (input: LoginInput) => {
    const authenticatedUser = await api.login(input);
    setUser(authenticatedUser);
    setSessionError(null);
    return authenticatedUser;
  }, []);

  const register = useCallback(
    async (input: CandidateRegistrationInput) => {
      await api.register(input);
      return login({ email: input.email, password: input.password });
    },
    [login],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setSessionError(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      sessionError,
      login,
      register,
      logout,
      refresh,
      homeForRole,
    }),
    [user, loading, sessionError, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
