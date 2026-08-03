import { useState } from "react";
import { api } from "../api/client";
import type { ToolConfig, ScanResult } from "../types";

interface ScanFormProps {
  tool: ToolConfig;
  onScanComplete: (input: string) => void;
}

export default function ScanForm({ tool, onScanComplete }: ScanFormProps) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<ScanResult | null>(null);

  const handleScan = async () => {
    if (!input.trim()) return;
    setLoading(true);
    setError(null);
    setLastResult(null);

    try {
      const res = await api.post<ScanResult>(tool.scanEndpoint(input.trim()));
      setLastResult(res.data);
      onScanComplete(input.trim());
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Scan failed. Check backend logs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border border-zinc-800 rounded-md bg-zinc-950 p-4 mb-6">
      <label className="block text-xs font-mono text-zinc-500 uppercase tracking-wider mb-2">
        {tool.inputLabel}
      </label>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={tool.inputPlaceholder}
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm font-mono text-zinc-200 focus:outline-none focus:border-emerald-500"
          onKeyDown={(e) => e.key === "Enter" && handleScan()}
        />
        <button
          onClick={handleScan}
          disabled={loading}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white text-sm font-mono rounded transition-colors"
        >
          {loading ? "Scanning..." : "Run Scan"}
        </button>
      </div>

      {error && (
        <p className="text-red-400 text-xs font-mono mt-3">⚠ {error}</p>
      )}

      {lastResult && (
        <p className="text-emerald-400 text-xs font-mono mt-3">
          ✓ Found {lastResult.total_found ?? 0} results — stored to database
        </p>
      )}
    </div>
  );
}