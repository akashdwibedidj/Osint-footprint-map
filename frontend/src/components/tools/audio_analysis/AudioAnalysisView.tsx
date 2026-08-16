// src/components/tools/audio_analysis/AudioAnalysisView.tsx
import { useEffect, useRef, useState } from "react";
import { api } from "../../../api/client";
import History from "../../History"; // adjust path to wherever History.tsx actually lives

interface AudioFinding {
  id: string;
  source: string;
  source_url: string;
  raw_value: string;
  category: string;
  risk_severity: string;
  extra_metadata?: Record<string, any>;
}

interface Segment {
  start: number;
  end: number;
  text: string;
}

interface SoundEvent {
  label: string;
  confidence: number;
}

function formatStage(stage?: string | null) {
  if (!stage) return "";
  return stage.replace(/_/g, " ");
}

function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${sec}`;
}

export default function AudioAnalysisView() {
  const [label, setLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [scanId, setScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<string | null>(null);
  const [stage, setStage] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const [findings, setFindings] = useState<AudioFinding[]>([]);
  const [loadingFindings, setLoadingFindings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAllSegments, setShowAllSegments] = useState(false);

  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isBusy = scanStatus === "pending" || scanStatus === "running";

  const fetchFindings = async (targetLabel: string) => {
    setLoadingFindings(true);
    setError(null);
    try {
      const encoded = encodeURIComponent(targetLabel.trim());
      const res = await api.get(`/audio_analysis/profile/${encoded}`);
      setFindings(res.data.findings);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load findings.");
    } finally {
      setLoadingFindings(false);
    }
  };

  const handleHistorySelect = (value: string) => {
    setLabel(value);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setScanId(null);
    setScanStatus(null);
    setStage(null);
    setProgress(0);
    setShowAllSegments(false);
    fetchFindings(value);
  };

  useEffect(() => {
    if (!scanId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const res = await api.get(`/audio_analysis/status/${scanId}`);
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
          timeoutRef.current = setTimeout(poll, 1500);
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
    setShowAllSegments(false);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("label", label.trim());
      const res = await api.post("/audio_analysis/upload", formData);
      setScanId(res.data.scan_id);
    } catch (err: any) {
      setScanStatus(null);
      setError(err?.response?.data?.detail || "Upload failed.");
    }
  };

  const transcript = findings.find((f) => f.extra_metadata?.field === "transcript");
  const audioFeatures = findings.find((f) => f.extra_metadata?.field === "audio_features");
  const soundEvents = findings.find((f) => f.extra_metadata?.field === "sound_events");

  const segments: Segment[] = transcript?.extra_metadata?.segments || [];
  const visibleSegments = showAllSegments ? segments : segments.slice(0, 5);

  const events: SoundEvent[] = soundEvents?.extra_metadata?.events || [];

  const featureRows: { label: string; value: string | number | null }[] = audioFeatures
    ? [
        { label: "Duration", value: `${audioFeatures.extra_metadata?.duration_s}s` },
        { label: "Tempo", value: `${audioFeatures.extra_metadata?.tempo_bpm} bpm` },
        { label: "Silence Ratio", value: audioFeatures.extra_metadata?.silence_ratio },
        {
          label: "Mean Pitch",
          value: audioFeatures.extra_metadata?.mean_pitch_hz
            ? `${audioFeatures.extra_metadata.mean_pitch_hz} Hz`
            : "n/a",
        },
        {
          label: "Spectral Centroid",
          value: `${audioFeatures.extra_metadata?.mean_spectral_centroid_hz} Hz`,
        },
      ]
    : [];

  const hasResults = transcript || audioFeatures || soundEvents;

  return (
    <div>
      <History toolId="audio_analysis" onSelect={handleHistorySelect} />

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
          Audio File
        </label>
        <div className="flex gap-2">
          <input
            type="file"
            accept="audio/*"
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
          Transcribes speech, extracts audio features (tempo, silence, pitch), and tags background sound events.
        </p>
      </div>

      {loadingFindings && <p className="text-zinc-500 font-mono text-sm">Loading findings...</p>}

      {!loadingFindings && !hasResults && !isBusy && (
        <p className="text-zinc-600 font-mono text-sm border border-zinc-800 rounded p-4">
          No findings yet, or no scan run.
        </p>
      )}

      {hasResults && (
        <div className="space-y-4">
          {transcript && (
            <div className="border border-zinc-800 rounded-md bg-zinc-950 p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-mono text-sm font-bold text-zinc-200">Transcript</h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border text-zinc-400 border-zinc-700">
                  {transcript.extra_metadata?.language} (
                  {Math.round((transcript.extra_metadata?.language_probability ?? 0) * 100)}%)
                </span>
              </div>
              <p className="text-zinc-300 text-sm font-mono whitespace-pre-wrap mb-3">
                {transcript.raw_value}
              </p>

              {segments.length > 0 && (
                <div className="border-t border-zinc-800 pt-2 mt-2">
                  <p className="text-zinc-600 text-[10px] font-mono uppercase mb-1.5">Segments</p>
                  <div className="space-y-1">
                    {visibleSegments.map((s, i) => (
                      <p key={i} className="text-zinc-500 text-[11px] font-mono">
                        <span className="text-zinc-600">
                          [{formatTime(s.start)}–{formatTime(s.end)}]
                        </span>{" "}
                        {s.text}
                      </p>
                    ))}
                  </div>
                  {segments.length > 5 && (
                    <button
                      onClick={() => setShowAllSegments((v) => !v)}
                      className="text-emerald-400 hover:underline text-[11px] font-mono mt-2"
                    >
                      {showAllSegments ? "Show fewer" : `Show all ${segments.length} segments`}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {audioFeatures && (
            <div className="border border-zinc-800 rounded-md bg-zinc-950 p-4">
              <h3 className="font-mono text-sm font-bold text-zinc-200 mb-2">Audio Features</h3>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                {featureRows.map((row) => (
                  <p key={row.label} className="text-zinc-500 text-[11px] font-mono">
                    <span className="text-zinc-600">{row.label}:</span> {row.value}
                  </p>
                ))}
              </div>
            </div>
          )}

          {soundEvents && events.length > 0 && (
            <div className="border border-zinc-800 rounded-md bg-zinc-950 p-4">
              <h3 className="font-mono text-sm font-bold text-zinc-200 mb-2">Sound Events</h3>
              <div className="flex flex-wrap gap-1.5">
                {events.map((e, i) => (
                  <span
                    key={i}
                    className="text-[10px] font-mono px-2 py-0.5 rounded border text-emerald-400 border-emerald-900"
                  >
                    {e.label} ({(e.confidence * 100).toFixed(0)}%)
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}