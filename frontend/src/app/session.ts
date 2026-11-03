import { useSyncExternalStore } from "react";
import { getToken, subscribeSession } from "../api/session";

// The current token as React state: any change (login, logout, 401) re-renders whoever uses it
export function useSessionToken(): string | null {
  return useSyncExternalStore(subscribeSession, getToken, () => null);
}
