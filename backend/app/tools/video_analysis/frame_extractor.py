"""
Extracts frames from a video at a fixed time interval using the bundled
imageio-ffmpeg binary via subprocess - same "no system-wide binary
dependency" approach as audio_analysis's conversion step. Deliberately
NOT using pydub/ffprobe here (that combination caused WinError 2 with
imageio-ffmpeg previously, since ffprobe isn't bundled).
"""

import os
import subprocess
import tempfile

import imageio_ffmpeg

FRAME_INTERVAL_S = 2.0


def get_video_duration_s(video_path: str) -> float:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    # ffmpeg (not ffprobe) prints duration to stderr when given -i with no output
    result = subprocess.run(
        [ffmpeg_exe, "-i", video_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for line in result.stderr.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            # "Duration: 00:00:12.34, start: ..."
            ts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = ts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def extract_frames(video_path: str) -> list[tuple[int, float, bytes]]:
    """
    Returns a list of (frame_index, timestamp_s, jpeg_bytes) sampled at
    FRAME_INTERVAL_S. Frame N of len(result) gives real progress reporting
    upstream, same role as Whisper's segment-based progress in audio.
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    duration_s = get_video_duration_s(video_path)
    if duration_s <= 0:
        return []

    frames: list[tuple[int, float, bytes]] = []
    timestamps = []
    t = 0.0
    while t < duration_s:
        timestamps.append(t)
        t += FRAME_INTERVAL_S

    with tempfile.TemporaryDirectory() as tmp_dir:
        for idx, ts in enumerate(timestamps):
            out_path = os.path.join(tmp_dir, f"frame_{idx}.jpg")
            subprocess.run(
                [
                    ffmpeg_exe, "-y",
                    "-ss", str(ts),
                    "-i", video_path,
                    "-frames:v", "1",
                    "-q:v", "2",
                    out_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if os.path.exists(out_path):
                with open(out_path, "rb") as f:
                    frames.append((idx, round(ts, 2), f.read()))

    return frames