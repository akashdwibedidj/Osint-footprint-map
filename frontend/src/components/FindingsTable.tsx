import type { Finding } from "../types";

interface FindingsTableProps {
  findings: Finding[];
  loading: boolean;
}

const categoryColor: Record<string, string> = {
  personal_identifier: "text-blue-400",
  contact_detail: "text-purple-400",
  credential: "text-red-400",
  behavioral_pattern: "text-yellow-400",
  organizational_link: "text-orange-400",
};

export default function FindingsTable({ findings, loading }: FindingsTableProps) {
  if (loading) {
    return <p className="text-zinc-500 font-mono text-sm">Loading findings...</p>;
  }

  if (findings.length === 0) {
    return (
      <p className="text-zinc-600 font-mono text-sm border border-zinc-800 rounded p-4">
        No findings yet. Run a scan above.
      </p>
    );
  }

  return (
    <div className="border border-zinc-800 rounded-md overflow-hidden">
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="bg-zinc-900 text-zinc-500 text-xs uppercase tracking-wider">
            <th className="text-left px-4 py-2">Source</th>
            <th className="text-left px-4 py-2">URL</th>
            <th className="text-left px-4 py-2">Category</th>
            <th className="text-left px-4 py-2">Risk</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((f, idx) => (
            <tr
              key={idx}
              className="border-t border-zinc-800 hover:bg-zinc-900/50 text-zinc-300"
            >
              <td className="px-4 py-2">{f.source}</td>
              <td className="px-4 py-2">
                <a
                  href={f.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 hover:underline"
                >
                  {f.source_url}
                </a>
              </td>
              <td className={`px-4 py-2 ${categoryColor[f.category] || "text-zinc-400"}`}>
                {f.category}
              </td>
              <td className="px-4 py-2 text-zinc-500">{f.risk_severity}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}