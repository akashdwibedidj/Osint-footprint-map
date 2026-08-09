import { useState, useRef } from "react";
import { api } from "../api/client";
import type { ToolConfig, ScanResult } from "../types";

interface ScanFormUploadProps {
  tool: ToolConfig;
  onScanComplete: (input: string, toolId?: string) => void;
}

export default function ScanFormUpload({ tool, onScanComplete }: ScanFormUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<ScanResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleScan = async () => {
    if (!file || !tool.uploadEndpoint) return;
    setLoading(true);
    setError(null);
    setLastResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await api.post<ScanResult>(tool.uploadEndpoint, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setLastResult(res.data);
      // backend returns "value" (the filename) — used as the key for fetchFindings/graph
      const returnedValue = (res.data as any).value || file.name;
      onScanComplete(returnedValue, tool.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Upload failed. Check backend logs.");
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
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm font-mono text-zinc-200 file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:bg-zinc-800 file:text-zinc-300 file:text-xs"
        />
        <button
          onClick={handleScan}
          disabled={loading || !file}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white text-sm font-mono rounded transition-colors"
        >
          {loading ? "Uploading..." : "Run Scan"}
        </button>
      </div>

      {error && <p className="text-red-400 text-xs font-mono mt-3">⚠ {error}</p>}

      {lastResult && (
        <p className="text-emerald-400 text-xs font-mono mt-3">
          ✓ Extracted findings — stored to database
        </p>
      )}
    </div>
  );
}