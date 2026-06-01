"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { streamUrl } from "@/lib/api";
import { ChatMessage, ToolCallCard } from "@/lib/types";
import RoutingCard from "./RoutingCard";

interface Props {
  token: string;
  onBalanceUpdate: (balance: number) => void;
}

let _msgCounter = 0;
function nextId() {
  return String(++_msgCounter);
}

export default function ChatWindow({ token, onBalanceUpdate }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Clean up on unmount
  useEffect(() => () => { esRef.current?.close(); }, []);

  function appendMsg(msg: ChatMessage) {
    setMessages((prev) => [...prev, msg]);
  }

  function patchLast(predicate: (m: ChatMessage) => boolean, patch: Partial<ChatMessage>) {
    setMessages((prev) => {
      const idx = [...prev].reverse().findIndex(predicate);
      if (idx === -1) return prev;
      const realIdx = prev.length - 1 - idx;
      const updated = [...prev];
      updated[realIdx] = { ...updated[realIdx], ...patch };
      if (patch.toolCard) {
        updated[realIdx].toolCard = { ...updated[realIdx].toolCard!, ...patch.toolCard };
      }
      return updated;
    });
  }

  function sendMessage() {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    setStreaming(true);

    // User bubble
    appendMsg({ id: nextId(), role: "user", text });

    const url = streamUrl(text, token);
    const es = new EventSource(url);
    esRef.current = es;

    es.addEventListener("thinking", (e) => {
      const d = JSON.parse(e.data);
      appendMsg({ id: nextId(), role: "thinking", text: d.message });
    });

    es.addEventListener("tool_start", (e) => {
      const d = JSON.parse(e.data);
      const card: ToolCallCard = {
        tool: d.tool,
        provider: d.provider,
        cost: 0,          // unknown until tool_result arrives
        status: "running",
      };
      appendMsg({ id: nextId(), role: "tool", toolCard: card });
    });

    es.addEventListener("tool_result", (e) => {
      const d = JSON.parse(e.data);
      patchLast(
        (m) => m.role === "tool" && m.toolCard?.tool === d.tool && m.toolCard?.status === "running",
        {
          toolCard: {
            tool: d.tool,
            provider: d.provider,
            cost: d.cost ?? 0,
            remainingCredits: d.remaining_credits ?? undefined,
            data: d.data,
            status: "done",
          },
        }
      );
      if (d.remaining_credits != null) onBalanceUpdate(d.remaining_credits);
    });

    es.addEventListener("tool_error", (e) => {
      const d = JSON.parse(e.data);
      patchLast(
        (m) => m.role === "tool" && m.toolCard?.tool === d.tool && m.toolCard?.status === "running",
        { toolCard: { ...({} as ToolCallCard), status: "error", errorMessage: d.error } }
      );
    });

    es.addEventListener("answer", (e) => {
      const d = JSON.parse(e.data);
      const msgId = nextId();
      // Start with empty text, then type out word by word
      appendMsg({ id: msgId, role: "assistant", text: "" });
      const words = (d.message as string).split(" ");
      let i = 0;
      const timer = setInterval(() => {
        i++;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId ? { ...m, text: words.slice(0, i).join(" ") } : m
          )
        );
        if (i >= words.length) clearInterval(timer);
      }, 40);
    });

    es.addEventListener("error", (e) => {
      // Covers both the "error" event type and network errors
      if (e instanceof MessageEvent) {
        const d = JSON.parse((e as MessageEvent).data);
        appendMsg({ id: nextId(), role: "error", text: d.message });
      }
      es.close();
      setStreaming(false);
    });

    es.addEventListener("done", (e) => {
      const d = JSON.parse((e as MessageEvent).data);
      if (d.balance != null) onBalanceUpdate(d.balance);
      es.close();
      setStreaming(false);
    });

    // Fallback for connection-level errors
    es.onerror = () => {
      es.close();
      setStreaming(false);
    };
  }

  return (
    <div className="flex flex-col flex-1 h-screen overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-800 bg-gray-950 flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-emerald-400" />
        <h1 className="text-sm font-semibold text-gray-200 tracking-wide">Agent Execution Console</h1>
        <span className="ml-auto text-xs text-gray-600 font-mono">SSE · /api/v1/stream</span>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-4 bg-gray-950">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-700 gap-2">
            <svg className="w-8 h-8 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <p className="text-sm">Send a message to start an agent run</p>
          </div>
        )}

        {messages.map((msg) => {
          if (msg.role === "user") {
            return (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-lg bg-violet-700 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed shadow">
                  {msg.text}
                </div>
              </div>
            );
          }

          if (msg.role === "thinking") {
            return (
              <div key={msg.id} className="flex items-center gap-2 text-gray-500 text-xs font-mono">
                <span className="animate-pulse">⟳</span>
                <span>{msg.text}</span>
              </div>
            );
          }

          if (msg.role === "tool" && msg.toolCard) {
            return (
              <div key={msg.id} className="max-w-xl">
                <RoutingCard card={msg.toolCard} />
              </div>
            );
          }

          if (msg.role === "assistant") {
            return (
              <div key={msg.id} className="flex flex-col gap-1">
                <div className="max-w-lg bg-gray-800 border border-gray-700 text-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed">
                  <div className="prose prose-invert prose-sm">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text ?? ""}</ReactMarkdown>
                  </div>
                </div>
                {msg.balanceAfter !== undefined && (
                  <p className="text-xs text-gray-600 font-mono ml-1">
                    balance after run: {msg.balanceAfter} cr
                  </p>
                )}
              </div>
            );
          }

          if (msg.role === "error") {
            return (
              <div key={msg.id} className="flex items-center gap-2 text-red-400 text-xs font-mono bg-red-950/30 border border-red-800 rounded-lg px-4 py-2">
                <span>✕</span>
                <span>{msg.text}</span>
              </div>
            );
          }

          return null;
        })}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-800 bg-gray-950">
        <div className="flex gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="Enter an instruction for the agent…"
            disabled={streaming}
            className="flex-1 bg-gray-900 border border-gray-700 text-white text-sm rounded-xl px-4 py-3 focus:outline-none focus:ring-1 focus:ring-violet-500 disabled:opacity-50 placeholder:text-gray-600"
          />
          <button
            onClick={sendMessage}
            disabled={streaming || !input.trim()}
            className="bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white px-5 rounded-xl font-semibold text-sm transition-colors flex items-center gap-2"
          >
            {streaming ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Running
              </>
            ) : "Run"}
          </button>
        </div>
      </div>
    </div>
  );
}
