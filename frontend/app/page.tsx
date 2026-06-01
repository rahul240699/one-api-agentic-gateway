"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import { fetchWalletActivity } from "@/lib/api";
import { clearSession, getSession, setSession } from "@/lib/auth";

export default function Home() {
  const router = useRouter();
  const session = typeof window !== "undefined" ? getSession() : null;
  const [apiKey] = useState<string>(session?.api_key ?? "");
  const [allKeys, setAllKeys] = useState<string[]>(session?.all_keys ?? (session?.api_key ? [session.api_key] : []));
  const [email] = useState<string>(session?.email ?? "");
  const [balance, setBalance] = useState<number | null>(null);

  useEffect(() => {
    if (!session) {
      router.replace("/login");
      return;
    }
    fetchWalletActivity(session.api_key)
      .then((d) => setBalance(d.balance))
      .catch(() => setBalance(0));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleKeysUpdated(newAllKeys: string[]) {
    setAllKeys(newAllKeys);
    if (session) setSession({ ...session, all_keys: newAllKeys });
  }

  function handleLogout() {
    clearSession();
    router.replace("/login");
  }

  if (!apiKey || balance === null) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-gray-500 text-sm">
        Connecting to gateway…
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <Sidebar
        apiKey={apiKey}
        allKeys={allKeys}
        email={email}
        balance={balance}
        onBalanceChange={setBalance}
        onKeysUpdated={handleKeysUpdated}
        onLogout={handleLogout}
      />
      <main className="flex-1 flex flex-col overflow-hidden">
        <ChatWindow apiKey={apiKey} onBalanceUpdate={setBalance} />
      </main>
    </div>
  );
}
