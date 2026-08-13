import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { HistoryItem } from "../types";

interface HistoryProps {
  toolId: string;
  onSelect: (username: string) => void;
}

export default function History({ toolId, onSelect }: HistoryProps) {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<HistoryItem[]>("/history")
      .then((res) => setItems(res.data.filter((i) => i.tool_id === toolId)))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [toolId]);

  if (loading || items.length === 0) return null;

  return (
    <div className="mb-6 border border-zinc-800 rounded-md bg-zinc-950 p-3">
      <p className="text-zinc-600 text-[10px] uppercase tracking-wider font-mono mb-2">
        Recent scans
      </p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <button
            key={item.target_id}
            onClick={() => onSelect(item.username)}
            className="px-2 py-1 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded text-xs font-mono text-zinc-300"
          >
            {item.username}
            <span className="text-zinc-600"> ({item.findings_count})</span>
          </button>
        ))}
      </div>
    </div>
  );
}