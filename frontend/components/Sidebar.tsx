"use client";

import { useState } from "react";
import { postTopup, formatCredits, generateApiKey } from "@/lib/api";

interface SidebarProps {
  apiKey: string;
  allKeys: string[];
  email: string;
  balance: number;
  onBalanceChange: (b: number) => void;
  onKeysUpdated: (keys: string[]) => void;
  onLogout: () => void;
}

const COST_TABLE = [
  { label: "Google Search",    tool: "web_search",       cost: 10 },
  { label: "Hunter.io Enrich", tool: "enrich_profile",   cost: 10 },
  { label: "Firecrawl Scrape", tool: "firecrawl_scrape", cost: 5  },
  { label: "Jina Reader",      tool: "jina_scrape",      cost: 2  },
  { label: "Weather",          tool: "get_weather",      cost: 1  },
];

function maskKey(key: string) {
  // show "sk-" prefix + first 4 chars + "••••••••" + last 4 chars
  return `${key.slice(0, 7)}••••••••${key.slice(-4)}`;
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }
  return (
    <button
      onClick={copy}
      title="Copy full key"
      className="ml-1.5 text-gray-500 hover:text-violet-400 transition-colors flex-shrink-0"
    >
      {copied ? (
        <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
    </button>
  );
}

export default function Sidebar({
  apiKey, allKeys, email, balance,
  onBalanceChange, onKeysUpdated, onLogout,
}: SidebarProps) {
  const [topupAmount, setTopupAmount] = useState("50");
  const [topupLoading, setTopupLoading] = useState(false);
  const [topupError, setTopupError] = useState<string | null>(null);
  const [genLoading, setGenLoading] = useState(false);

  async function handleTopup() {
    const amount = parseInt(topupAmount, 10);
    if (!amount || amount <= 0) return;
    setTopupLoading(true);
    setTopupError(null);
    try {
      const res = await postTopup(apiKey, amount);
      onBalanceChange(res.new_balance);
    } catch (e) {
      setTopupError(e instanceof Error ? e.message : "Top-up failed");
    } finally {
      setTopupLoading(false);
    }
  }

  async function handleGenerateKey() {
    setGenLoading(true);
    try {
      const res = await generateApiKey(apiKey);
      onKeysUpdated(res.all_keys);
    } catch {
      // silently ignore — key generation failure is non-critical
    } finally {
      setGenLoading(false);
    }
  }

  return (
    <aside className="w-72 min-h-screen bg-gray-950 border-r border-gray-800 flex flex-col p-5 gap-6 overflow-y-auto">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">Agent Wallet</p>
          <p className="text-xs text-gray-300 font-medium">{email}</p>
        </div>
        <button
          onClick={onLogout}
          className="text-xs text-gray-600 hover:text-red-400 transition-colors mt-0.5"
        >
          Sign out
        </button>
      </div>

      {/* Balance */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Balance</p>
        <p className={`text-4xl font-bold font-mono tabular-nums transition-colors duration-300 ${
          balance <= 10 ? "text-red-400" : balance <= 30 ? "text-yellow-400" : "text-emerald-400"
        }`}>
          {formatCredits(balance)}
        </p>
        <p className="text-xs text-gray-600 mt-1">credits remaining</p>
      </div>

      {/* API Keys */}
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-gray-500 uppercase tracking-wider">API Keys</p>
          <button
            onClick={handleGenerateKey}
            disabled={genLoading}
            className="text-[10px] font-semibold text-violet-400 hover:text-violet-300 disabled:opacity-50 transition-colors flex items-center gap-1"
          >
            {genLoading ? (
              <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            ) : (
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/>
              </svg>
            )}
            Generate
          </button>
        </div>

        <div className="flex flex-col gap-2">
          {allKeys.map((key, i) => (
            <div
              key={key}
              className={`flex items-center rounded-lg px-2.5 py-2 border ${
                key === apiKey
                  ? "border-violet-700/50 bg-violet-950/20"
                  : "border-gray-800 bg-gray-800/40"
              }`}
            >
              <span className="flex-1 font-mono text-[10px] text-gray-400 truncate">
                {maskKey(key)}
              </span>
              {i === 0 && (
                <span className="text-[9px] font-bold text-violet-500 mr-1.5 uppercase tracking-wide">
                  Active
                </span>
              )}
              <CopyButton value={key} />
            </div>
          ))}
        </div>
      </div>

      {/* Top-up */}
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <p className="text-xs text-gray-500 mb-3 uppercase tracking-wider">Load Budget</p>
        <div className="flex gap-2 mb-2">
          <input
            type="number"
            min="1"
            value={topupAmount}
            onChange={(e) => setTopupAmount(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono"
          />
          <button
            onClick={handleTopup}
            disabled={topupLoading}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold px-4 rounded-lg transition-colors"
          >
            {topupLoading ? "..." : "Top Up"}
          </button>
        </div>
        {topupError && <p className="text-red-400 text-xs mt-1">{topupError}</p>}
      </div>

      {/* Tool costs */}
      <div>
        <p className="text-xs text-gray-500 mb-3 uppercase tracking-wider">Tool Costs</p>
        <div className="flex flex-col gap-2">
          {COST_TABLE.map((row) => (
            <div
              key={row.tool}
              className="flex justify-between items-center py-2 px-3 rounded-lg bg-gray-900 border border-gray-800"
            >
              <span className="text-xs text-gray-300">{row.label}</span>
              <span className="text-xs font-mono font-semibold text-violet-400">{row.cost} cr</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-auto">
        <p className="text-xs text-gray-700 text-center">Agentic Commerce Gateway</p>
      </div>
    </aside>
  );
}
