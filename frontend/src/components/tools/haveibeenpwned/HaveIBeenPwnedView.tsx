import { useState } from "react";
import { api } from "../../../api/client";

interface HibpFinding {
  source: string;
  source_url: string;
  raw_value: string;
  category: string;
  risk_severity: string;
  extra_metadata?: Record<string, any>;
}

export default function HaveIBeenPwnedView() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [findings, setFindings] = useState<HibpFinding[]>([]);
  const [error, setError] = useState<string | null>(null);

  const runScan = async () => {
    if (!email.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.post(`/haveibeenpwned/email/${email.trim()}`);
      const res = await api.get(`/haveibeenpwned/email/${email.trim()}`);
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
          Email
        </label>
        <div className="flex gap-2">
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="e.g. user@example.com"
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm font-mono text-zinc-200 focus:outline-none focus:border-emerald-500"
            onKeyDown={(e) => e.key === "Enter" && runScan()}
          />
          <button
            onClick={runScan}
            disabled={loading}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 text-white text-sm font-mono rounded"
          >
            {loading ? "Checking..." : "Run Scan"}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs font-mono mt-3">⚠ {error}</p>}
      </div>

      {findings.length === 0 && !loading && (
        <p className="text-zinc-600 font-mono text-sm border border-zinc-800 rounded p-4">
          No breaches checked yet, or none found.
        </p>
      )}

      {findings.length > 0 && (
        <div className="space-y-3">
          {findings.map((f, idx) => {
            const meta = f.extra_metadata || {};
            const dataClasses: string[] = meta.data_classes || [];
            return (
              <div key={idx} className="border border-zinc-800 rounded-md bg-zinc-950 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-red-400 font-mono text-sm font-bold">
                    {meta.breach_title || f.raw_value}
                  </h3>
                  <span className="text-zinc-500 text-xs font-mono">{meta.breach_date}</span>
                </div>
                <p className="text-zinc-500 text-xs font-mono mb-2">
                  Domain: {meta.breach_domain || "—"} · Records: {meta.pwn_count?.toLocaleString?.() || "—"}
                </p>
                <div className="flex flex-wrap gap-1">
                  {dataClasses.map((dc, i) => (
                    <span
                      key={i}
                      className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 text-yellow-400 border border-zinc-800"
                    >
                      {dc}
                    </span>
                  ))}
                </div>
                {(meta.is_verified === false || meta.is_sensitive) && (
                  <p className="text-xs font-mono mt-2 text-zinc-500">
                    {meta.is_sensitive && <span className="text-orange-400 mr-2">⚠ Sensitive breach</span>}
                    {meta.is_verified === false && <span>Unverified</span>}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}