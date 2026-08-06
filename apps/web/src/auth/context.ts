import { createContext } from "react";
import type {
  CandidateRegistrationInput,
  LoginInput,
  Role,
  User,
} from "../types/domain";

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  sessionError: string | null;
  login: (input: LoginInput) => Promise<User>;
  register: (input: CandidateRegistrationInput) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  homeForRole: (role: Role) => string;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
