import os

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def is_image(filename: str) -> bool:
    return os.path.splitext(filename or "")[1].lower() in IMAGE_EXTS


def is_video(filename: str) -> bool:
    return os.path.splitext(filename or "")[1].lower() in VIDEO_EXTS


def cleanup_file(path: str | None) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass