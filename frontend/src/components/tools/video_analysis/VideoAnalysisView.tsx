// src/components/tools/video_analysis/VideoAnalysisView.tsx
import { useEffect, useRef, useState } from "react";
import { api } from "../../../api/client";
import History from "../../History"; // adjust path to wherever History.tsx actually lives

interface VideoFinding {
  id: string;
  source: string;
  source_url: string;
  raw_value: string;
  category: string;
  risk_severity: string;
  extra_metadata?: Record<string, any>;
}

interface FrameGroup {
  frame_index: number;
  timestamp_s: number;
  caption?: string;
  objects?: { label: string; confidence: number }[];
  gps?: Record<string, any>;
  landmark?: Record<string, any>;
  terrain?: Record<string, any>;
  environment?: Record<string, any>;
  ocr?: string;
}

const fieldBadge: Record<string, string> = {
  objects_detected: "text-emerald-400 border-emerald-900",
  image_caption: "text-zinc-400 border-zinc-700",
  gps_coordinates: "text-blue-400 border-blue-900",
  landmark_recognition: "text-purple-400 border-purple-900",
  terrain_structure: "text-orange-400 border-orange-900",
  environmental_signature: "text-teal-400 border-teal-900",
  ocr_text: "text-pink-400 border-pink-900",
};

function formatStage(stage?: string | null) {
  if (!stage) return "";
  return stage.replace(/_/g, " ");
}

function omit(obj: Record<string, any>, keys: string[]) {
  const out: Record<string, any> = {};
  for (const k of Object.keys(obj)) {
    if (!keys.includes(k)) out[k] = obj[k];
  }
  return out;
}

function buildFrameGroups(findings: VideoFinding[]): FrameGroup[] {
  const byFrame = new Map<number, FrameGroup>();

  for (const f of findings) {
    const meta = f.extra_metadata || {};
    const frameIndex = meta.frame_index ?? 0;
    const timestamp = meta.timestamp_s ?? 0;

    if (!byFrame.has(frameIndex)) {
      byFrame.set(frameIndex, { frame_index: frameIndex, timestamp_s: timestamp });
    }
    const group = byFrame.get(frameIndex)!;

    switch (meta.field) {
      case "objects_detected":
        group.objects = meta.detections || [];
        break;
      case "image_caption":
        group.caption = f.raw_value;
        break;
      case "gps_coordinates":
        group.gps = meta.location || omit(meta, ["field", "frame_index", "timestamp_s"]);
        break;
      case "landmark_recognition":
        group.landmark = omit(meta, ["field", "frame_index", "timestamp_s"]);
        break;
      case "terrain_structure":
        group.terrain = omit(meta, ["field", "frame_index", "timestamp_s"]);
        break;
      case "environmental_signature":
        group.environment = omit(meta, ["field", "frame_index", "timestamp_s"]);
        break;
      case "ocr_text":
        group.ocr = f.raw_value;
        break;
      default:
        break;
    }
  }

  return Array.from(byFrame.values()).sort((a, b) => a.frame_index - b.frame_index);
}

function KeyValueList({ data }: { data: Record<string, any> }) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (entries.length === 0) return null;
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
      {entries.map(([k, v]) => (
        <p key={k} className="text-zinc-500 text-[11px] font-mono">
          <span className="text-zinc-600">{k.replace(/_/g, " ")}:</span> {String(v)}
        </p>
      ))}
    </div>
  );
}

export default function VideoAnalysisView() {
  const [label, setLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [scanId, setScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<string | null>(null);
  const [stage, setStage] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const [findings, setFindings] = useState<VideoFinding[]>([]);
  const [loadingFindings, setLoadingFindings] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isBusy = scanStatus === "pending" || scanStatus === "running";

  const fetchFindings = async (targetLabel: string) => {
    setLoadingFindings(true);
    setError(null);
    try {
      const encoded = encodeURIComponent(targetLabel.trim());
      const res = await api.get(`/video_analysis/profile/${encoded}`);
      setFindings(res.data.findings);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load findings.");
    } finally {
      setLoadingFindings(false);
    }
  };

  const handleHistorySelect = (value: string) => {
    setLabel(value);
    // clear any in-flight/previous scan state - this is a fetch, not a rescan
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setScanId(null);
    setScanStatus(null);
    setStage(null);
    setProgress(0);
    fetchFindings(value);
  };

  useEffect(() => {
    if (!scanId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const res = await api.get(`/video_analysis/status/${scanId}`);
        if (cancelled) return;
        const data = res.data;
        setStage(data.stage);
        setProgress(data.progress ?? 0);
        setScanStatus(data.status);

        if (data.status === "done") {
          await fetchFindings(label);
        } else if (data.status === "failed") {
          setError(data.error_message || "Scan failed.");
        } else {
          timeoutRef.current = setTimeout(poll, 2000);
        }
      } catch {
        if (!cancelled) setError("Failed to fetch scan status.");
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanId]);

  const runScan = async () => {
    if (!file || !label.trim()) return;
    setError(null);
    setFindings([]);
    setScanId(null);
    setScanStatus("pending");
    setProgress(0);
    setStage(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("label", label.trim());
      const res = await api.post("/video_analysis/upload", formData);
      setScanId(res.data.scan_id);
    } catch (err: any) {
      setScanStatus(null);
      setError(err?.response?.data?.detail || "Upload failed.");
    }
  };

  const frameGroups = buildFrameGroups(findings);

  return (
    <div>
      <History toolId="video_analysis" onSelect={handleHistorySelect} />

      <div className="border border-zinc-800 rounded-md bg-zinc-950 p-4 mb-6">
        <label className="block text-xs font-mono text-zinc-500 uppercase tracking-wider mb-2">
          Target Label
        </label>
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g. john_doe_case_01"
          className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm font-mono text-zinc-200 focus:outline-none focus:border-emerald-500 mb-3"
        />

        <label className="block text-xs font-mono text-zinc-500 uppercase tracking-wider mb-2">
          Image or Video File
        </label>
        <div className="flex gap-2">
          <input
            type="file"
            accept="image/*,video/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-xs font-mono text-zinc-300 file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:bg-emerald-600 file:text-white file:text-xs"
          />
          <button
            onClick={runScan}
            disabled={isBusy || !file || !label.trim()}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 text-white text-sm font-mono rounded whitespace-nowrap"
          >
            {isBusy ? "Scanning..." : "Run Scan"}
          </button>
        </div>

        {error && <p className="text-red-400 text-xs font-mono mt-3">⚠ {error}</p>}

        {isBusy && (
          <div className="mt-4">
            <div className="flex justify-between text-[10px] font-mono text-zinc-500 uppercase mb-1">
              <span>{formatStage(stage)}</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full h-1.5 bg-zinc-800 rounded overflow-hidden">
              <div
                className="h-full bg-emerald-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        <p className="text-zinc-600 text-[10px] font-mono mt-3">
          Images are analyzed directly; videos are frame-sampled first. Detects objects, generates captions,
          and extracts GPS/landmark/terrain/environment/OCR signals per frame.
        </p>
      </div>

      {loadingFindings && (
        <p className="text-zinc-500 font-mono text-sm">Loading findings...</p>
      )}

      {!loadingFindings && frameGroups.length === 0 && !isBusy && (
        <p className="text-zinc-600 font-mono text-sm border border-zinc-800 rounded p-4">
          No findings yet, or no scan run.
        </p>
      )}

      {frameGroups.length > 0 && (
        <div className="space-y-4">
          {frameGroups.map((group) => (
            <div key={group.frame_index} className="border border-zinc-800 rounded-md bg-zinc-950 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-mono text-sm font-bold text-zinc-200">
                  Frame {group.frame_index}
                </h3>
                <span className="text-[10px] font-mono text-zinc-600">
                  t={group.timestamp_s.toFixed(2)}s
                </span>
              </div>

              {group.caption && (
                <p className={`text-xs font-mono mb-2 px-2 py-1 rounded border inline-block ${fieldBadge.image_caption}`}>
                  {group.caption}
                </p>
              )}

              {group.objects && group.objects.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {group.objects.map((o, i) => (
                    <span
                      key={i}
                      className={`text-[10px] font-mono px-2 py-0.5 rounded border ${fieldBadge.objects_detected}`}
                    >
                      {o.label} ({(o.confidence * 100).toFixed(0)}%)
                    </span>
                  ))}
                </div>
              )}

              {group.gps && (
                <div className={`text-xs font-mono mb-2 px-2 py-1.5 rounded border ${fieldBadge.gps_coordinates}`}>
                  <p className="uppercase text-[10px] mb-1 opacity-70">GPS</p>
                  <KeyValueList data={group.gps} />
                </div>
              )}

              {group.landmark && (
                <div className={`text-xs font-mono mb-2 px-2 py-1.5 rounded border ${fieldBadge.landmark_recognition}`}>
                  <p className="uppercase text-[10px] mb-1 opacity-70">Landmark</p>
                  <KeyValueList data={group.landmark} />
                </div>
              )}

              {group.terrain && (
                <div className={`text-xs font-mono mb-2 px-2 py-1.5 rounded border ${fieldBadge.terrain_structure}`}>
                  <p className="uppercase text-[10px] mb-1 opacity-70">Terrain</p>
                  <KeyValueList data={group.terrain} />
                </div>
              )}

              {group.environment && (
                <div className={`text-xs font-mono mb-2 px-2 py-1.5 rounded border ${fieldBadge.environmental_signature}`}>
                  <p className="uppercase text-[10px] mb-1 opacity-70">Environment</p>
                  <KeyValueList data={group.environment} />
                </div>
              )}

              {group.ocr && (
                <div className={`text-xs font-mono px-2 py-1.5 rounded border ${fieldBadge.ocr_text}`}>
                  <p className="uppercase text-[10px] mb-1 opacity-70">OCR Text</p>
                  <p className="text-zinc-300 whitespace-pre-wrap">{group.ocr}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}