// Session = the JWT in localStorage. Components read it through useSessionToken (app/session.ts).
// Known risk: any XSS can read localStorage. The token lasts 60 minutes and there is no refresh.

const TOKEN_KEY = "comanda.token";
const EXPIRED_KEY = "comanda.sessionExpired";

type Listener = () => void;
const listeners = new Set<Listener>();

function notify(): void {
  listeners.forEach((listener) => listener());
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    sessionStorage.removeItem(EXPIRED_KEY);
  } catch {
    // storage blocked: the session simply will not persist
  }
  notify();
}

// expired=true leaves a flag so the login screen can say "Tu sesión venció"
export function clearSession(options: { expired?: boolean } = {}): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    if (options.expired) sessionStorage.setItem(EXPIRED_KEY, "1");
  } catch {
    // nothing else to clean
  }
  notify();
}

// Reads the "session expired" flag once (it disappears after being read)
export function consumeSessionExpired(): boolean {
  try {
    const expired = sessionStorage.getItem(EXPIRED_KEY) === "1";
    sessionStorage.removeItem(EXPIRED_KEY);
    return expired;
  } catch {
    return false;
  }
}

export function subscribeSession(listener: Listener): () => void {
  listeners.add(listener);
  // Logging out in another tab also logs out this one
  const onStorage = (event: StorageEvent) => {
    if (event.key === TOKEN_KEY) listener();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}
