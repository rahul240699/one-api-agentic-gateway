export interface Session {
  email: string;
  api_key: string;       // active key used for requests
  all_keys: string[];    // all keys for the account
}

const SESSION_KEY = "oneapi_session";

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as Session;
    // Migrate old sessions that don't have all_keys
    if (!s.all_keys) s.all_keys = [s.api_key];
    return s;
  } catch {
    return null;
  }
}

export function setSession(session: Session): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
}
