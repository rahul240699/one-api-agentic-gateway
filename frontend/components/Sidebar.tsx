"use client";

import { useState } from "react";
import { postTopup, formatCredits } from "@/lib/api";

interface SidebarProps {
  token: string;
  balance: number;
  onBalanceChange: (b: number) => void;
}

const COST_TABLE = [
  { label: "Google Search",      tool: "web_search",       cost: 10 },
  { label: "Hunter.io Enrich",   tool: "enrich_profile",   cost: 10 },
  { label: "Firecrawl Scrape",   tool: "firecrawl_scrape", cost: 5  },
  { label: "Jina Reader",        tool: "jina_scrape",      cost: 2  },
  { label: "Weather",            tool: "get_weather",      cost: 1  },
];

export default function Sidebar({ token, balance, onBalanceChange }: SidebarProps) {
  const [topupAmount, setTopupAmount] = useState("50");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleTopup() {
    const amount = parseInt(topupAmount, 10);
    if (!amount || amount <= 0) return;
    setLoading(true);
    setError(null);
    try {
      const res = await postTopup(token, amount);
      onBalanceChange(res.new_balance);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Top-up failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className="w-72 min-h-screen bg-gray-950 border-r border-gray-800 flex flex-col p-5 gap-6">
      {/* Header */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">
          Agent Wallet
        </p>
        <p className="text-xs text-gray-600 font-mono">{token}</p>
      </div>

      {/* Balance */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Balance</p>
        <p
          className={`text-4xl font-bold font-mono tabular-nums transition-colors duration-300 ${
            balance <= 10 ? "text-red-400" : balance <= 30 ? "text-yellow-400" : "text-emerald-400"
          }`}
        >
          {formatCredits(balance)}
        </p>
        <p className="text-xs text-gray-600 mt-1">credits remaining</p>
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
            placeholder="Amount"
          />
          <button
            onClick={handleTopup}
            disabled={loading}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold px-4 rounded-lg transition-colors"
          >
            {loading ? "..." : "Top Up"}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
      </div>

      {/* Cost reference */}
      <div>
        <p className="text-xs text-gray-500 mb-3 uppercase tracking-wider">Tool Costs</p>
        <div className="flex flex-col gap-2">
          {COST_TABLE.map((row) => (
            <div
              key={row.tool}
              className="flex justify-between items-center py-2 px-3 rounded-lg bg-gray-900 border border-gray-800"
            >
              <span className="text-xs text-gray-300">{row.label}</span>
              <span className="text-xs font-mono font-semibold text-violet-400">
                {row.cost} cr
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-auto">
        <p className="text-xs text-gray-700 text-center">Agentic Commerce Gateway</p>
      </div>
    </aside>
  );
}
