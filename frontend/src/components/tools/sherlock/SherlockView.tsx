import { useState } from "react";
import { api } from "../../../api/client";

interface SherlockFinding {
  source: string;
  source_url: string;
  category: string;
  risk_severity: string;
}

export default function SherlockView() {
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [findings, setFindings] = useState<SherlockFinding[]>([]);
  const [error, setError] = useState<string | null>(null);

  const runScan = async () => {
    if (!username.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.post(`/scan/username/${username.trim()}`);
      const res = await api.get(`/scan/username/${username.trim()}`);
      setFindings(res.data.findings);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Scan failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="border border-zinc-800 rounded-md bg-zinc-950 p-4 mb-6">
        <label className="block text-xs font-mono text-zinc-500 uppercase tracking-wider mb-2">
          Username
        </label>
        <div className="flex gap-2">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g. zachking"
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm font-mono text-zinc-200 focus:outline-none focus:border-emerald-500"
            onKeyDown={(e) => e.key === "Enter" && runScan()}
          />
          <button
            onClick={runScan}
            disabled={loading}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 text-white text-sm font-mono rounded"
          >
            {loading ? "Scanning..." : "Run Scan"}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs font-mono mt-3">⚠ {error}</p>}
      </div>

      {findings.length > 0 && (
        <div className="border border-zinc-800 rounded-md overflow-hidden">
          <table className="w-full text-sm font-mono">
            <thead>
              <tr className="bg-zinc-900 text-zinc-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-2">Source</th>
                <th className="text-left px-4 py-2">URL</th>
                <th className="text-left px-4 py-2">Risk</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f, idx) => (
                <tr key={idx} className="border-t border-zinc-800 text-zinc-300">
                  <td className="px-4 py-2">{f.source}</td>
                  <td className="px-4 py-2">
                    <a href={f.source_url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">
                      {f.source_url}
                    </a>
                  </td>
                  <td className="px-4 py-2 text-zinc-500">{f.risk_severity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}