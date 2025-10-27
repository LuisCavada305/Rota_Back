import { useAuth as useAuthContext, type User } from "./AuthContext";

export type { User };

export function useAuth() {
  // Wrapper to keep existing import paths without triggering extra `/me` requests.
  return useAuthContext();
}
