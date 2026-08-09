import { useState } from "react";
import { api } from "../../../api/client";

interface ExifFinding {
  source: string;
  source_url: string;
  raw_value: string;
  category: string;
  risk_severity: string;
  extra_metadata?: Record<string, any>;
}

export default function ExifExtractorView() {
  const [mode, setMode] = useState<"url" | "upload">("url");
  const [imageUrl, setImageUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [findings, setFindings] = useState<ExifFinding[]>([]);
  const [error, setError] = useState<string | null>(null);

  const runUrlScan = async () => {
    if (!imageUrl.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const encoded = encodeURIComponent(imageUrl.trim());
      await api.post(`/exif_extractor/image_url/${encoded}`);
      const res = await api.get(`/exif_extractor/image_url/${encoded}`);
      setFindings(res.data.findings);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Scan failed.");
    } finally {
      setLoading(false);
    }
  };

  const runUploadScan = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const postRes = await api.post(`/exif_extractor/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const value = postRes.data.value || file.name;
      const res = await api.get(`/exif_extractor/image_url/${encodeURIComponent(value)}`);
      setFindings(res.data.findings);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="border border-zinc-800 rounded-md bg-zinc-950 p-4 mb-6">
        <div className="flex gap-1 mb-3 border border-zinc-800 rounded overflow-hidden w-fit">
          <button
            onClick={() => setMode("url")}
            className={`px-3 py-1 text-xs font-mono ${mode === "url" ? "bg-emerald-600 text-white" : "bg-zinc-900 text-zinc-400"}`}
          >
            Image URL
          </button>
          <button
            onClick={() => setMode("upload")}
            className={`px-3 py-1 text-xs font-mono ${mode === "upload" ? "bg-emerald-600 text-white" : "bg-zinc-900 text-zinc-400"}`}
          >
            Local Upload
          </button>
        </div>

        {mode === "url" ? (
          <div className="flex gap-2">
            <input
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              placeholder="https://example.com/photo.jpg"
              className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm font-mono text-zinc-200 focus:outline-none focus:border-emerald-500"
              onKeyDown={(e) => e.key === "Enter" && runUrlScan()}
            />
            <button
              onClick={runUrlScan}
              disabled={loading}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 text-white text-sm font-mono rounded"
            >
              {loading ? "Scanning..." : "Run Scan"}
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm font-mono text-zinc-200 file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:bg-zinc-800 file:text-zinc-300 file:text-xs"
            />
            <button
              onClick={runUploadScan}
              disabled={loading || !file}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 text-white text-sm font-mono rounded"
            >
              {loading ? "Uploading..." : "Run Scan"}
            </button>
          </div>
        )}
        {error && <p className="text-red-400 text-xs font-mono mt-3">⚠ {error}</p>}
      </div>

      {findings.length === 0 && !loading && (
        <p className="text-zinc-600 font-mono text-sm border border-zinc-800 rounded p-4">
          No EXIF data extracted yet.
        </p>
      )}

      {findings.length > 0 && (
        <div className="space-y-3">
          {findings.map((f, idx) => {
            const meta = f.extra_metadata || {};
            return (
              <div key={idx} className="border border-zinc-800 rounded-md bg-zinc-950 p-4">
                {meta.gps ? (
                  <>
                    <h3 className="text-yellow-400 font-mono text-sm font-bold mb-1">📍 GPS Location</h3>
                    <p className="text-zinc-300 text-xs font-mono mb-2">
                      {meta.gps.latitude.toFixed(6)}, {meta.gps.longitude.toFixed(6)}
                    </p>
                    <a
                      href={`https://www.google.com/maps?q=${meta.gps.latitude},${meta.gps.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-400 hover:underline text-xs font-mono"
                    >
                      View on map →
                    </a>
                  </>
                ) : meta.device_info ? (
                  <>
                    <h3 className="text-blue-400 font-mono text-sm font-bold mb-1">📷 Device Info</h3>
                    <p className="text-zinc-300 text-xs font-mono">{f.raw_value}</p>
                  </>
                ) : (
                  <>
                    <h3 className="text-zinc-400 font-mono text-sm font-bold mb-2">Raw EXIF Data</h3>
                    <div className="text-xs font-mono text-zinc-500 space-y-1">
                      {meta.raw_exif &&
                        Object.entries(meta.raw_exif).map(([k, v]) => (
                          <p key={k}>
                            <span className="text-zinc-600">{k}:</span> {String(v)}
                          </p>
                        ))}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}