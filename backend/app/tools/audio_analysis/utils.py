# app/tools/audio_analysis/utils.py

"""
Audio format conversion helpers for audio_analysis.
Whisper/librosa/YAMNet all want a consistent, decodable waveform - we
normalize whatever gets uploaded (mp3, m4a, ogg, wav, ...) to 16kHz mono
WAV via ffmpeg once, up front, and every downstream step reads that
single normalized file.

Uses the `imageio-ffmpeg` pip package for the ffmpeg binary itself - it
ships a static binary inside the venv (site-packages), so there's nothing
to install system-wide and no PATH/admin dependency. Add `imageio-ffmpeg`
to requirements.txt.

We call ffmpeg directly via subprocess rather than through pydub:
pydub's AudioSegment.from_file() also shells out to a separate `ffprobe`
binary to inspect the file before converting, and imageio-ffmpeg only
bundles `ffmpeg`, not `ffprobe`. ffmpeg auto-detects the input format on
its own, so probing isn't actually needed for our use case - and duration
is computed downstream via librosa/soundfile anyway.
"""

import os
import subprocess

import imageio_ffmpeg

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
TARGET_SAMPLE_RATE = 16000


def convert_to_wav(src_path: str, dst_path: str) -> None:
    """
    Converts src_path (any ffmpeg-readable format - audio or video, only
    the audio track is used) to a 16kHz mono WAV at dst_path.
    """
    result = subprocess.run(
        [
            FFMPEG_EXE,
            "-y",  # overwrite dst_path if it already exists
            "-i", src_path,
            "-ar", str(TARGET_SAMPLE_RATE),
            "-ac", "1",
            "-vn",  # drop any video stream, audio only
            dst_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.strip()[-1000:]}")


def cleanup_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass