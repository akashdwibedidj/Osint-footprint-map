# app/tools/audio_analysis/model_loader.py

"""
Loads the audio_analysis models once as module-level singletons instead
of per-request - Whisper/YAMNet load times are far too slow to pay on
every scan (same reasoning as instaloader's per-process loader instance,
just formalized here since we have two heavy models).
"""

import csv

from faster_whisper import WhisperModel

from app.config import settings

_whisper_model: WhisperModel | None = None
_yamnet_model = None
_yamnet_class_names: list[str] | None = None


def get_whisper_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _whisper_model


def get_yamnet_model():
    """
    Returns (model, class_names). tensorflow/tensorflow_hub are imported
    lazily here so a process that never hits audio_analysis doesn't pay
    the (large) TF import cost on every startup.
    """
    global _yamnet_model, _yamnet_class_names
    if _yamnet_model is None:
        import tensorflow as tf
        import tensorflow_hub as hub

        # TF grabs the entire GPU memory pool by default, which would starve
        # faster-whisper (CTranslate2) sharing the same 6GB card. Let it grow
        # on demand instead of pre-allocating everything.
        for gpu in tf.config.list_physical_devices("GPU"):
            tf.config.experimental.set_memory_growth(gpu, True)

        _yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")
        class_map_path = _yamnet_model.class_map_path().numpy().decode("utf-8")
        _yamnet_class_names = _load_class_names(class_map_path)
    return _yamnet_model, _yamnet_class_names


def _load_class_names(class_map_csv_path: str) -> list[str]:
    import tensorflow as tf

    with tf.io.gfile.GFile(class_map_csv_path) as f:
        reader = csv.reader(f)
        next(reader)  # header row: index,mid,display_name
        return [row[2] for row in reader]