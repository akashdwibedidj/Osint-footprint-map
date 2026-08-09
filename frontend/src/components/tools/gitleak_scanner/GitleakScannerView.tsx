import { useState } from "react";
import { api } from "../../../api/client";

interface GitleaksFinding {
  source: string;
  source_url: string;
  raw_value: string;
  category: string;
  risk_severity: string;
  extra_metadata?: Record<string, any>;
}

const severityColor: Record<string, string> = {
  high: "text-red-400 border-red-900",
  medium: "text-yellow-400 border-yellow-900",
};

export default function GitleakScannerView() {
  const [repo, setRepo] = useState("");
  const [loading, setLoading] = useState(false);
  const [findings, setFindings] = useState<GitleaksFinding[]>([]);
  const [error, setError] = useState<string | null>(null);

  const runScan = async () => {
    if (!repo.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const encoded = encodeURIComponent(repo.trim());
      await api.post(`/gitleak_scanner/repo/${encoded}`);
      const res = await api.get(`/gitleak_scanner/repo/${encoded}`);
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
          Repository (owner/repo or full git URL)
        </label>
        <div className="flex gap-2">
          <input
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="e.g. torvalds/linux or https://github.com/owner/repo.git"
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
        <p className="text-zinc-600 text-[10px] font-mono mt-2">
          Clones the repo (depth 1) and scans full commit history for leaked secrets. May take up to ~2 min on large repos.
        </p>
      </div>

      {findings.length === 0 && !loading && (
        <p className="text-zinc-600 font-mono text-sm border border-zinc-800 rounded p-4">
          No leaks found yet, or no scan run.
        </p>
      )}

      {findings.length > 0 && (
        <div className="space-y-3">
          {findings.map((f, idx) => {
            const meta = f.extra_metadata || {};
            const sev = meta.severity_hint || "medium";
            return (
              <div
                key={idx}
                className={`border rounded-md bg-zinc-950 p-4 ${severityColor[sev] || "border-zinc-800"}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-mono text-sm font-bold text-zinc-200">{meta.rule_id || "unknown_rule"}</h3>
                  <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${severityColor[sev] || ""}`}>
                    {sev}
                  </span>
                </div>
                <p className="text-zinc-400 text-xs font-mono mb-1">
                  {meta.file}{meta.line_start != null ? `:${meta.line_start}` : ""}
                </p>
                <div className="text-zinc-500 text-[11px] font-mono space-y-0.5 mt-2">
                  {meta.commit && <p>Commit: {String(meta.commit).slice(0, 10)}</p>}
                  {meta.author && <p>Author: {meta.author}{meta.author_email ? ` <${meta.author_email}>` : ""}</p>}
                  {meta.commit_date && <p>Date: {meta.commit_date}</p>}
                  {meta.secret_redacted && <p>Secret: {meta.secret_redacted}</p>}
                </div>
                <a
                  href={f.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 hover:underline text-xs font-mono inline-block mt-2"
                >
                  View repo →
                </a>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}