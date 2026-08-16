"""
Loads video_analysis models once as module-level singletons instead of
per-request - same reasoning/pattern as audio_analysis/model_loader.py.
All three models are PyTorch-based (ultralytics + transformers) - no
second ML framework, deliberately, to avoid repeating the TF/setuptools
dependency break hit with YAMNet.
"""

from app.config import settings

_yolo_model = None
_blip_processor = None
_blip_model = None
_clip_processor = None
_clip_model = None


def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        _yolo_model = YOLO(settings.yolo_model_name)  # e.g. "yolov8n.pt"
    return _yolo_model


def get_blip_model():
    global _blip_processor, _blip_model
    if _blip_model is None:
        from transformers import BlipForConditionalGeneration, BlipProcessor

        _blip_processor = BlipProcessor.from_pretrained(settings.blip_model_name)
        _blip_model = BlipForConditionalGeneration.from_pretrained(settings.blip_model_name)
        _blip_model.to(settings.video_device)
        _blip_model.eval()
    return _blip_processor, _blip_model


def get_clip_model():
    global _clip_processor, _clip_model
    if _clip_model is None:
        from transformers import CLIPModel, CLIPProcessor

        _clip_processor = CLIPProcessor.from_pretrained(settings.clip_model_name)
        _clip_model = CLIPModel.from_pretrained(settings.clip_model_name)
        _clip_model.to(settings.video_device)
        _clip_model.eval()
    return _clip_processor, _clip_model