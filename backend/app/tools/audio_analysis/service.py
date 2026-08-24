# app/tools/audio_analysis/service.py

import os
import uuid
from datetime import datetime, timezone

import librosa
import numpy as np

from app.core.tool_base import NormalizedFinding
from app.db.postgres import SessionLocal
from app.models.finding import ExposureCategory
from app.models.scan import Scan
from app.models.target import Target
from app.services import storage
from app.tools.audio_analysis import model_loader, utils

TOOL_ID = "audio_analysis"
ACCEPTED_INPUTS = {"audio", "video"}
# How much of the overall 0-100 progress bar each real stage accounts for.
# This isn't a time estimate - it's just how we split the bar across the
# ordered steps so "progress" only ever reflects work actually completed
# (transcription segment N/M done, feature extraction finished, etc.),
# never a simulated/fake tick.
STAGE_WEIGHTS = {
    "transcribing": (0, 60),
    "analyzing_audio_features": (60, 75),
    "tagging_sounds": (75, 95),
    "storing": (95, 100),
}


def _set_scan(scan_id: uuid.UUID, **fields) -> None:
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return
        for k, v in fields.items():
            setattr(scan, k, v)
        db.commit()
    finally:
        db.close()


def _set_stage_progress(scan_id: uuid.UUID, stage: str, fraction: float) -> None:
    """fraction: 0.0-1.0 of real completion *within* this stage."""
    lo, hi = STAGE_WEIGHTS[stage]
    progress = int(lo + (hi - lo) * max(0.0, min(1.0, fraction)))
    _set_scan(scan_id, status="running", stage=stage, progress=progress)


def _transcribe(wav_path: str, duration_s: float, scan_id: uuid.UUID) -> dict:
    model = model_loader.get_whisper_model()
    segments_gen, info = model.transcribe(wav_path, beam_size=5)

    segments = []
    full_text_parts = []
    for seg in segments_gen:
        segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
        full_text_parts.append(seg.text.strip())
        # Real progress: faster-whisper yields segments as it decodes them,
        # and each segment carries its own end-timestamp, so we know exactly
        # how much of the audio's duration has actually been transcribed.
        if duration_s > 0:
            _set_stage_progress(scan_id, "transcribing", seg.end / duration_s)

    _set_stage_progress(scan_id, "transcribing", 1.0)

    return {
        "text": " ".join(full_text_parts).strip(),
        "segments": segments,
        "language": info.language,
        "language_probability": info.language_probability,
    }


def _extract_audio_features(wav_path: str, duration_s: float) -> dict:
    y, sr = librosa.load(wav_path, sr=None, mono=True)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    # librosa.beat.beat_track returns tempo as an array (not a plain scalar)
    # in current versions, and numpy no longer allows float() on non-0-d
    # arrays - pull out the first estimate explicitly instead.
    tempo_bpm = float(np.asarray(tempo).reshape(-1)[0])

    rms = librosa.feature.rms(y=y)[0]
    silence_ratio = float(np.mean(rms < (0.02 * np.max(rms)))) if np.max(rms) > 0 else 1.0

    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = pitches[magnitudes > np.median(magnitudes)]
    mean_pitch = float(np.mean(pitch_values)) if pitch_values.size else None

    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]

    return {
        "duration_s": round(duration_s, 2),
        "tempo_bpm": round(tempo_bpm, 2),
        "silence_ratio": round(silence_ratio, 4),
        "mean_pitch_hz": round(mean_pitch, 2) if mean_pitch else None,
        "mean_spectral_centroid_hz": round(float(np.mean(spectral_centroid)), 2),
    }


def _tag_sound_events(wav_path: str, top_n: int = 5) -> list[dict]:
    import soundfile as sf

    model, class_names = model_loader.get_yamnet_model()

    waveform, sr = sf.read(wav_path, dtype="float32")
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)  # already mono from utils.convert_to_wav, safety net

    scores, embeddings, spectrogram = model(waveform)
    mean_scores = scores.numpy().mean(axis=0)

    top_indices = mean_scores.argsort()[-top_n:][::-1]
    return [
        {"label": class_names[i], "confidence": round(float(mean_scores[i]), 4)}
        for i in top_indices
    ]


def _build_findings(
    source_url: str, transcript: dict, features: dict, sound_events: list[dict]
) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []

    if transcript["text"]:
        findings.append(NormalizedFinding(
            source=TOOL_ID,
            source_url=source_url,
            raw_value=transcript["text"],
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            extra_metadata={
                "field": "transcript",
                "language": transcript["language"],
                "language_probability": transcript["language_probability"],
                "segments": transcript["segments"],
            },
        ))

    findings.append(NormalizedFinding(
        source=TOOL_ID,
        source_url=source_url,
        raw_value=f"tempo={features['tempo_bpm']}bpm duration={features['duration_s']}s",
        category=ExposureCategory.BEHAVIORAL_PATTERN,
        extra_metadata={"field": "audio_features", **features},
    ))

    if sound_events:
        findings.append(NormalizedFinding(
            source=TOOL_ID,
            source_url=source_url,
            raw_value=", ".join(e["label"] for e in sound_events),
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            extra_metadata={"field": "sound_events", "events": sound_events},
        ))

    return findings

def run_from_path(target_label: str, file_path: str, investigation_id: uuid.UUID | None = None) -> uuid.UUID:
    db = SessionLocal()
    try:
        target = db.query(Target).filter(Target.label == target_label).first()
        if not target:
            target = Target(label=target_label)
            db.add(target)
            db.flush()

        scan = Scan(
            target_id=target.id,
            tool_used=TOOL_ID,
            status="pending",
            progress=0,
            investigation_id=investigation_id,
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        scan_id = scan.id
    finally:
        db.close()

    wav_path = os.path.join(os.path.dirname(file_path), f"{scan_id}.wav")
    utils.convert_to_wav(file_path, wav_path)

    process_audio_job(scan_id, target_label, file_path, wav_path)

    return scan_id

def process_audio_job(scan_id: uuid.UUID, target_label: str, original_path: str, wav_path: str) -> None:
    """
    Entry point run as a FastAPI BackgroundTask. Owns the full lifecycle of
    one scan: transcribe -> audio features -> sound tagging -> store ->
    mark done/failed. Opens its own DB sessions throughout since it runs
    outside the request/response cycle (the request's `db` dependency is
    already closed by the time this runs).
    """
    try:
        _set_scan(scan_id, status="running", stage="transcribing", progress=0)

        duration_s = librosa.get_duration(path=wav_path)

        transcript = _transcribe(wav_path, duration_s, scan_id)

        _set_stage_progress(scan_id, "analyzing_audio_features", 0.0)
        features = _extract_audio_features(wav_path, duration_s)
        _set_stage_progress(scan_id, "analyzing_audio_features", 1.0)

        _set_stage_progress(scan_id, "tagging_sounds", 0.0)
        sound_events = _tag_sound_events(wav_path)
        _set_stage_progress(scan_id, "tagging_sounds", 1.0)

        _set_stage_progress(scan_id, "storing", 0.0)
        findings = _build_findings(
            source_url=f"local_upload://{os.path.basename(original_path)}",
            transcript=transcript,
            features=features,
            sound_events=sound_events,
        )

        db = SessionLocal()
        try:
            storage.store_findings(TOOL_ID, target_label, findings, db)
        finally:
            db.close()

        from app.db.neo4j import driver
        with driver.session() as session:
            storage.store_graph(
                tool_id=TOOL_ID,
                target_label=target_label,
                findings=findings,
                session=session,
                identifier_type="audio_upload",
            )

        _set_scan(
            scan_id,
            status="done",
            stage="storing",
            progress=100,
            finished_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        _set_scan(scan_id, status="failed", error_message=f"{type(e).__name__}: {e}")

    finally:
        utils.cleanup_file(wav_path)