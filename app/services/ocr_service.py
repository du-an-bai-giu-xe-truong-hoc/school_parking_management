"""YOLOv8 + Google Vision OCR service for license plate extraction."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from google.cloud import vision

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

logger = logging.getLogger(__name__)

_CREDENTIALS_PATH = Path(__file__).resolve().parents[1] / "core" / "mvbl-492911-81f79d8de732.json"
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(_CREDENTIALS_PATH))

_vision_client = vision.ImageAnnotatorClient()
_yolo_model = None


def _get_yolo_model():
    global _yolo_model
    if _yolo_model is not None:
        return _yolo_model

    if YOLO is None:
        logger.warning("YOLO package unavailable; fallback to full-image OCR")
        return None

    model_path = os.getenv("YOLO_PLATE_MODEL_PATH", "ai_modules/best.pt")
    model_file = Path(model_path)
    if not model_file.exists():
        logger.warning("YOLO model not found at %s; fallback to full-image OCR", model_path)
        return None

    try:
        _yolo_model = YOLO(str(model_file))
        return _yolo_model
    except Exception as exc:
        logger.warning("Cannot load YOLO model %s: %s", model_file, exc)
        return None


def _ocr_with_google_vision(image_content: bytes) -> Optional[str]:
    try:
        image = vision.Image(content=image_content)
        image_context = vision.ImageContext(language_hints=["vi"])
        response = _vision_client.text_detection(image=image, image_context=image_context)
        texts = response.text_annotations
        if not texts:
            return None
        return texts[0].description.replace("\n", " ").strip()
    except Exception as exc:
        logger.error("Google Vision OCR error: %s", exc)
        return None


def _extract_plate_crop_with_yolo(image_content: bytes) -> Optional[bytes]:
    model = _get_yolo_model()
    if model is None:
        return None

    np_arr = np.frombuffer(image_content, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        return None

    try:
        results = model(frame, verbose=False)
        if not results or len(results[0].boxes) == 0:
            return None

        box = max(results[0].boxes, key=lambda item: float(item.conf[0]))
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(frame.shape[1], x2)
        y2 = min(frame.shape[0], y2)
        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]
        ok, buffer = cv2.imencode(".jpg", crop)
        if not ok:
            return None
        return buffer.tobytes()
    except Exception as exc:
        logger.warning("YOLO inference failed, fallback to full image OCR: %s", exc)
        return None


def normalize_plate_text(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().upper())


async def get_license_plate_text(image_content: bytes):
    """Backward-compatible helper kept for existing camera endpoint."""
    result = await extract_plate_text_with_yolo_vision(image_content)
    return result


async def extract_plate_text_with_yolo_vision(image_content: bytes) -> Optional[str]:
    """Detect plate region with YOLOv8 then OCR with Google Vision.

    Fallback flow:
    1. YOLO crop + Vision OCR.
    2. Full-image Vision OCR if YOLO unavailable/fails.
    """
    if not image_content:
        return None

    crop_bytes = _extract_plate_crop_with_yolo(image_content)
    if crop_bytes is not None:
        text = _ocr_with_google_vision(crop_bytes)
        if text:
            return normalize_plate_text(text)

    full_text = _ocr_with_google_vision(image_content)
    if full_text:
        return normalize_plate_text(full_text)

    return None