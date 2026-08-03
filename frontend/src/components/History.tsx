import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { HistoryItem } from "../types";

interface HistoryProps {
  onSelect: (username: string, toolId: string) => void;
}

export default function History({ onSelect }: HistoryProps) {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/scan/history")
      .then((res) => setItems(res.data.targets))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-zinc-600 font-mono text-xs">Loading history...</p>;
  }

  if (items.length === 0) {
    return (
      <p className="text-zinc-600 font-mono text-xs border border-zinc-800 rounded p-3">
        No scans yet. Run one above.
      </p>
    );
  }

  return (
    <div className="border border-zinc-800 rounded-md bg-zinc-950 mb-6">
      <p className="px-3 py-2 text-[10px] uppercase tracking-wider text-zinc-500 font-mono border-b border-zinc-800">
        Previously scanned
      </p>
      <div className="max-h-40 overflow-y-auto">
        {items.map((item) => (
          <button
            key={item.target_id}
            onClick={() => onSelect(item.username, item.tool_id)}
            className="w-full flex items-center justify-between px-3 py-2 text-xs font-mono text-zinc-300 hover:bg-zinc-900 border-b border-zinc-900 last:border-0"
          >
            <div className="flex items-center gap-2">
              <span>{item.username}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500">
                {item.tool_id}
              </span>
            </div>
            <span className="text-zinc-600">{item.findings_count} findings</span>
          </button>
        ))}
      </div>
    </div>
  );
}