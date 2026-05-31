// API client — typed wrappers around the FastAPI backend.

const BASE = "http://localhost:8000";

export const DEFAULT_TOKEN = "ui-agent";

// Credit costs (mirrors config.py)
export const TOOL_COSTS: Record<string, number> = {
  enrich_profile: 10,
  scrape_page: 5,
  execute_action: 5,
};

// Display cost as a dollar-style label (1 credit = $0.01)
export function formatCredits(credits: number): string {
  return `${credits} cr`;
}
export function formatCost(credits: number): string {
  return `-${credits} cr`;
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

export async function fetchWalletActivity(token: string): Promise<WalletActivity> {
  const res = await fetch(`${BASE}/api/v1/wallet/activity`, {
    headers: { "X-Payment-Token": token },
  });
  if (!res.ok) throw new Error(`wallet/activity ${res.status}`);
  return res.json();
}

export async function postTopup(token: string, amount: number): Promise<TopupResponse> {
  const res = await fetch(`${BASE}/api/v1/wallet/topup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, amount }),
  });
  if (!res.ok) throw new Error(`topup ${res.status}`);
  return res.json();
}

// SSE stream URL — the browser opens this as EventSource
export function streamUrl(message: string, token: string): string {
  const p = new URLSearchParams({ message, token });
  return `${BASE}/api/v1/stream?${p}`;
}
