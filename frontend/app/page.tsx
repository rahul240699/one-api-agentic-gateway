"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import { fetchWalletActivity, DEFAULT_TOKEN } from "@/lib/api";

export default function Home() {
  const token = DEFAULT_TOKEN;
  const [balance, setBalance] = useState<number | null>(null);

  useEffect(() => {
    fetchWalletActivity(token)
      .then((d) => setBalance(d.balance))
      .catch(() => setBalance(0));
  }, [token]);

  if (balance === null) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-gray-500 text-sm">
        Connecting to gateway…
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <Sidebar token={token} balance={balance} onBalanceChange={setBalance} />
      <main className="flex-1 flex flex-col overflow-hidden">
        <ChatWindow token={token} onBalanceUpdate={setBalance} />
      </main>
    </div>
  );
}
