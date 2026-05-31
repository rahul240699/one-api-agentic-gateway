// Terminal-style card rendered when an agent tool call is in flight or complete.

import { ToolCallCard } from "@/lib/types";

interface Props {
  card: ToolCallCard;
}

export default function RoutingCard({ card }: Props) {
  const isRunning = card.status === "running";
  const isError = card.status === "error";

  return (
    <div
      className={`rounded-xl border font-mono text-xs overflow-hidden transition-all ${
        isError
          ? "border-red-700 bg-red-950/40"
          : isRunning
          ? "border-violet-700 bg-violet-950/30 animate-pulse"
          : "border-gray-700 bg-gray-900/60"
      }`}
    >
      {/* Header bar */}
      <div
        className={`flex items-center justify-between px-4 py-2 border-b ${
          isError ? "border-red-800 bg-red-900/30" : "border-gray-800 bg-gray-900"
        }`}
      >
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isError ? "bg-red-500" : isRunning ? "bg-violet-400 animate-ping" : "bg-emerald-400"
            }`}
          />
          <span className="text-gray-300 font-semibold tracking-wide">{card.provider}</span>
        </div>
        <span
          className={`text-xs font-bold px-2 py-0.5 rounded ${
            isError
              ? "text-red-400 bg-red-900/50"
              : "text-violet-300 bg-violet-900/50"
          }`}
        >
          {card.tool}
        </span>
      </div>

      {/* Body */}
      <div className="px-4 py-3 flex flex-col gap-2">
        {/* Cost line */}
        <div className="flex items-center justify-between">
          <span className="text-gray-500">Transaction cost</span>
          <span className="text-rose-400 font-bold">-{card.cost} cr</span>
        </div>

        {card.remainingCredits !== undefined && (
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Remaining balance</span>
            <span
              className={`font-bold ${
                card.remainingCredits <= 10
                  ? "text-red-400"
                  : card.remainingCredits <= 30
                  ? "text-yellow-400"
                  : "text-emerald-400"
              }`}
            >
              {card.remainingCredits} cr
            </span>
          </div>
        )}

        {/* Running spinner */}
        {isRunning && (
          <div className="flex items-center gap-2 text-violet-400 mt-1">
            <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span>Executing…</span>
          </div>
        )}

        {/* Error */}
        {isError && card.errorMessage && (
          <p className="text-red-400 mt-1">{card.errorMessage}</p>
        )}

        {/* Result preview */}
        {card.status === "done" && card.data && (
          <details className="mt-1">
            <summary className="cursor-pointer text-gray-500 hover:text-gray-300 transition-colors">
              View payload ▸
            </summary>
            <pre className="mt-2 text-gray-400 text-[10px] leading-relaxed whitespace-pre-wrap break-all">
              {JSON.stringify(card.data, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}
