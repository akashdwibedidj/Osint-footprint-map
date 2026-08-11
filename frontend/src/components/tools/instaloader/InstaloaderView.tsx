import { useState } from "react";
import { api } from "../../../api/client";

interface InstaFinding {
  source: string;
  source_url: string;
  raw_value: string;
  category: string;
  risk_severity: string;
  extra_metadata?: Record<string, any>;
}

interface ProfileMeta {
  followers?: number;
  followees?: number;
  mediacount?: number;
  is_private?: boolean;
  is_verified?: boolean;
  is_business_account?: boolean;
  business_category_name?: string | null;
}

const API_BASE = "http://localhost:8000"; // matches api/client.ts baseURL

function proxied(url: string | undefined): string | undefined {
  if (!url) return url;
  return `${API_BASE}/instaloader/image_proxy?url=${encodeURIComponent(url)}`;
}

export default function InstaloaderView() {
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [findings, setFindings] = useState<InstaFinding[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedPost, setSelectedPost] = useState<InstaFinding | null>(null);

  const runScan = async () => {
    const value = username.trim().replace(/^@/, "");
    if (!value) return;
    setLoading(true);
    setError(null);
    setSelectedPost(null);
    try {
      await api.post(`/instaloader/profile/${encodeURIComponent(value)}`);
      const res = await api.get(`/instaloader/profile/${encodeURIComponent(value)}`);
      setFindings(res.data.findings);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Scan failed.");
    } finally {
      setLoading(false);
    }
  };

  const fullName = findings.find((f) => f.extra_metadata?.field === "full_name")?.raw_value;
  const bio = findings.find((f) => f.extra_metadata?.field === "biography")?.raw_value;
  const externalUrl = findings.find((f) => f.extra_metadata?.field === "external_url")?.raw_value;
  const businessEmail = findings.find((f) => f.extra_metadata?.field === "business_email")?.raw_value;
  const businessPhone = findings.find((f) => f.extra_metadata?.field === "business_phone_number")?.raw_value;
  const avatarFinding = findings.find((f) => f.extra_metadata?.field === "profile_pic_url");
  const avatarUrl = avatarFinding?.raw_value;
  const meta: ProfileMeta = avatarFinding?.extra_metadata || {};

  const posts = findings.filter((f) => f.extra_metadata?.field === "post_image");

  return (
    <div>
      {/* Search bar */}
      <div className="border border-zinc-800 rounded-md bg-zinc-950 p-4 mb-6">
        <div className="flex gap-2">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username (no @, no url)"
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

      {findings.length === 0 && !loading && (
        <p className="text-zinc-600 font-mono text-sm border border-zinc-800 rounded p-4">
          No profile data loaded yet.
        </p>
      )}

      {findings.length > 0 && (
        <div className="border border-zinc-800 rounded-md bg-zinc-950 overflow-hidden">
          {/* Profile header - Instagram style */}
          <div className="p-6 border-b border-zinc-800">
            <div className="flex items-start gap-6">
              <div className="shrink-0">
                {avatarUrl ? (
                  <img
                    src={proxied(avatarUrl)}
                    alt="avatar"
                    referrerPolicy="no-referrer"
                    className="w-24 h-24 rounded-full object-cover border-2 border-zinc-800"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                ) : (
                  <div className="w-24 h-24 rounded-full bg-zinc-800" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 flex-wrap mb-3">
                  <h2 className="text-zinc-100 font-mono text-lg">{username.replace(/^@/, "")}</h2>
                  {meta.is_verified && (
                    <span className="text-blue-400 text-xs font-mono border border-blue-400/40 rounded px-1.5 py-0.5">
                      ✓ verified
                    </span>
                  )}
                  {meta.is_private && (
                    <span className="text-yellow-400 text-xs font-mono border border-yellow-400/40 rounded px-1.5 py-0.5">
                      🔒 private
                    </span>
                  )}
                  {meta.is_business_account && (
                    <span className="text-purple-400 text-xs font-mono border border-purple-400/40 rounded px-1.5 py-0.5">
                      business{meta.business_category_name ? `: ${meta.business_category_name}` : ""}
                    </span>
                  )}
                </div>

                <div className="flex gap-6 mb-3 font-mono text-sm">
                  <span className="text-zinc-300">
                    <b className="text-white">{meta.mediacount ?? posts.length}</b> posts
                  </span>
                  <span className="text-zinc-300">
                    <b className="text-white">{meta.followers ?? "—"}</b> followers
                  </span>
                  <span className="text-zinc-300">
                    <b className="text-white">{meta.followees ?? "—"}</b> following
                  </span>
                </div>

                {fullName && <p className="text-zinc-200 font-mono text-sm font-bold">{fullName}</p>}
                {bio && <p className="text-zinc-400 font-mono text-sm whitespace-pre-wrap mt-1">{bio}</p>}
                {externalUrl && (
                  <a
                    href={externalUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-400 hover:underline text-xs font-mono block mt-1"
                  >
                    🔗 {externalUrl}
                  </a>
                )}
                {businessEmail && (
                  <p className="text-zinc-400 text-xs font-mono mt-1">✉ {businessEmail}</p>
                )}
                {businessPhone && (
                  <p className="text-zinc-400 text-xs font-mono mt-1">☎ {businessPhone}</p>
                )}
              </div>
            </div>
          </div>

          {/* Post grid */}
          <div className="p-4">
            <p className="text-zinc-600 text-[10px] uppercase tracking-wider font-mono mb-3">
              {posts.length} post{posts.length !== 1 ? "s" : ""} loaded
              {meta.is_private && posts.length === 0 ? " (private account — posts unavailable)" : ""}
            </p>

            {posts.length > 0 && (
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-1">
                {posts.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedPost(p)}
                    className="relative aspect-square bg-zinc-900 overflow-hidden group"
                  >
                    <img
                      src={proxied(p.raw_value)}
                      alt={p.extra_metadata?.shortcode || `post-${idx}`}
                      referrerPolicy="no-referrer"
                      className="w-full h-full object-cover group-hover:opacity-70 transition-opacity"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    {p.extra_metadata?.is_video && (
                      <span className="absolute top-1 right-1 text-white text-xs drop-shadow">▶</span>
                    )}
                    {p.extra_metadata?.location && (
                      <span className="absolute bottom-1 left-1 text-white text-[10px] drop-shadow">📍</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Post detail modal */}
      {selectedPost && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedPost(null)}
        >
          <div
            className="bg-zinc-950 border border-zinc-800 rounded-md max-w-2xl w-full flex flex-col md:flex-row overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="md:w-1/2 bg-black flex items-center justify-center">
              <img
                src={proxied(selectedPost.raw_value)}
                alt="post"
                referrerPolicy="no-referrer"
                className="max-h-[70vh] w-full object-contain"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            </div>
            <div className="md:w-1/2 p-4 space-y-2 font-mono text-xs">
              <button
                onClick={() => setSelectedPost(null)}
                className="text-zinc-500 hover:text-zinc-300 float-right"
              >
                ✕
              </button>
              {selectedPost.extra_metadata?.is_video && (
                <p className="text-zinc-400">▶ Video post</p>
              )}
              {selectedPost.extra_metadata?.caption && (
                <p className="text-zinc-300 whitespace-pre-wrap">{selectedPost.extra_metadata?.caption}</p>
              )}
              <p className="text-zinc-500">❤ {selectedPost.extra_metadata?.likes ?? "—"} likes</p>
              <p className="text-zinc-500">💬 {selectedPost.extra_metadata?.comments ?? "—"} comments</p>
              {selectedPost.extra_metadata?.location && (
                <p className="text-zinc-500">📍 {selectedPost.extra_metadata?.location}</p>
              )}
              {selectedPost.extra_metadata?.tagged_users?.length > 0 && (
                <p className="text-zinc-500">
                  🏷 {selectedPost.extra_metadata?.tagged_users.join(", ")}
                </p>
              )}
              {selectedPost.extra_metadata?.date_utc && (
                <p className="text-zinc-600">
                  {new Date(selectedPost.extra_metadata?.date_utc).toLocaleString()}
                </p>
              )}
              
              <a
                href={selectedPost.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-400 hover:underline block pt-2"
              >
                View on Instagram →
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}