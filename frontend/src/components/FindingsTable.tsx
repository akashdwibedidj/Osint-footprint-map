import type { Finding } from "../types";

interface FindingsTableProps {
  findings: Finding[];
  loading: boolean;
  toolId?: string;  // "sherlock" | "maigret" | etc.
}

const categoryColor: Record<string, string> = {
  personal_identifier: "text-blue-400",
  contact_detail: "text-purple-400",
  credential: "text-red-400",
  behavioral_pattern: "text-yellow-400",
  organizational_link: "text-orange-400",
};

export default function FindingsTable({ findings, loading, toolId }: FindingsTableProps) {
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

  const isMaigret = toolId === "maigret";

  return (
    <div className="border border-zinc-800 rounded-md overflow-hidden">
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="bg-zinc-900 text-zinc-500 text-xs uppercase tracking-wider">
            {isMaigret && <th className="text-left px-4 py-2 w-12">Img</th>}
            <th className="text-left px-4 py-2">Source</th>
            {isMaigret && <th className="text-left px-4 py-2">Name</th>}
            <th className="text-left px-4 py-2">URL</th>
            {isMaigret && <th className="text-left px-4 py-2">Followers</th>}
            <th className="text-left px-4 py-2">Category</th>
            <th className="text-left px-4 py-2">Risk</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((f, idx) => {
            const meta = f.extra_metadata || {};
            return (
              <tr
                key={idx}
                className="border-t border-zinc-800 hover:bg-zinc-900/50 text-zinc-300"
              >
                {isMaigret && (
                  <td className="px-4 py-2">
                    {meta.image ? (
                      <img
                        src={meta.image}
                        alt="profile"
                        className="w-8 h-8 rounded-full object-cover"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                    ) : (
                      <span className="text-zinc-600">—</span>
                    )}
                  </td>
                )}
                <td className="px-4 py-2">{f.source}</td>
                {isMaigret && (
                  <td className="px-4 py-2 text-zinc-400 text-xs">
                    {meta.fullname || "—"}
                    {meta.is_verified === "True" && (
                      <span className="ml-1 text-blue-400">✓</span>
                    )}
                  </td>
                )}
                <td className="px-4 py-2">
                  <a
                    href={f.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-400 hover:underline truncate max-w-[200px] inline-block"
                  >
                    {f.source_url}
                  </a>
                </td>
                {isMaigret && (
                  <td className="px-4 py-2 text-zinc-400 text-xs">
                    {meta.follower_count ? (
                      <span>
                        {Number(meta.follower_count).toLocaleString()}
                        {meta.following_count && ` / ${Number(meta.following_count).toLocaleString()}`}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                )}
                <td className={`px-4 py-2 ${categoryColor[f.category] || "text-zinc-400"}`}>
                  {f.category}
                </td>
                <td className="px-4 py-2 text-zinc-500">{f.risk_severity}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}