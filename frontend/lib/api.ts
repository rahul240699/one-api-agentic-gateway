// API client — typed wrappers around the FastAPI backend.

const BASE = "http://localhost:8000";
export const AUTH_HEADER = "X-OneAPI-Key";

export function formatCredits(credits: number): string {
  return `${credits} cr`;
}

export interface TxEntry {
  kind: "debit" | "credit" | "topup";
  amount: number;
  balance_after: number;
  service: string | null;
  success: boolean;
  timestamp: string;
}

export interface WalletActivity {
  token: string;
  balance: number;
  history: TxEntry[];
}

export interface TopupResponse {
  token: string;
  amount_added: number;
  new_balance: number;
  currency: string;
}

export interface AuthResponse {
  email: string;
  api_key: string;
  balance: number;
}

export async function register(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `register ${res.status}`);
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `login ${res.status}`);
  }
  return res.json();
}

export async function fetchWalletActivity(apiKey: string): Promise<WalletActivity> {
  const res = await fetch(`${BASE}/api/v1/wallet/activity`, {
    headers: { [AUTH_HEADER]: apiKey },
  });
  if (!res.ok) throw new Error(`wallet/activity ${res.status}`);
  return res.json();
}

export async function postTopup(apiKey: string, amount: number): Promise<TopupResponse> {
  const res = await fetch(`${BASE}/api/v1/wallet/topup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      [AUTH_HEADER]: apiKey,
    },
    body: JSON.stringify({ amount }),
  });
  if (!res.ok) throw new Error(`topup ${res.status}`);
  return res.json();
}

export interface NewKeyResponse {
  api_key: string;
  all_keys: string[];
}

export async function generateApiKey(currentKey: string): Promise<NewKeyResponse> {
  const res = await fetch(`${BASE}/api/v1/auth/keys`, {
    method: "POST",
    headers: { [AUTH_HEADER]: currentKey },
  });
  if (!res.ok) throw new Error(`generate key ${res.status}`);
  return res.json();
}

export async function listApiKeys(currentKey: string): Promise<string[]> {
  const res = await fetch(`${BASE}/api/v1/auth/keys`, {
    headers: { [AUTH_HEADER]: currentKey },
  });
  if (!res.ok) throw new Error(`list keys ${res.status}`);
  return res.json();
}

// SSE stream URL — the browser opens this as EventSource
export function streamUrl(message: string, apiKey: string): string {
  const p = new URLSearchParams({ message, token: apiKey });
  return `${BASE}/api/v1/stream?${p}`;
}
