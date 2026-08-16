import type { ToolConfig } from "../types";

export const TOOLS: ToolConfig[] = [
  { id: "sherlock", label: "Sherlock — Username Search" },
  { id: "maigret", label: "Maigret — Username Search" },
  { id: "haveibeenpwned", label: "HaveIBeenPwned — Email Breach Check" },
  { id: "exif_extractor", label: "EXIF Extractor — Image Metadata" },
  { id: "gitleak_scanner", label: "Gitleaks — Repo Secret Scan" },
  { id: "instaloader", label: "Instaloader — Instagram Profile Scan" },
  { id: "video_analysis", label: "Video Analysis — Frame Object/Scene Detection" },
  { id: "audio_analysis", label: "Audio Analysis — Transcript & Sound Tagging" },
];