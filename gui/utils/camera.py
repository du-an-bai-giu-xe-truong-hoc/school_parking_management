import base64
import os
import re
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import customtkinter as ctk
import cv2
import numpy as np
import requests
from PIL import Image

try:
    from pyzbar.pyzbar import decode as zbar_decode
except Exception:
    zbar_decode = None

try:
    from google.cloud import vision
except Exception:
    vision = None

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


_YOLO_LOCK = threading.Lock()
_YOLO_MODEL = None

_VISION_LOCK = threading.Lock()
_VISION_CLIENT = None


def _get_yolo_model():
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL

    if YOLO is None:
        return None

    model_path = os.getenv("YOLO_PLATE_MODEL_PATH", "ai_modules/best.pt")
    model_file = Path(model_path)
    if not model_file.exists():
        return None

    with _YOLO_LOCK:
        if _YOLO_MODEL is None:
            try:
                _YOLO_MODEL = YOLO(str(model_file))
            except Exception:
                _YOLO_MODEL = None
    return _YOLO_MODEL


def _ensure_google_credential_env() -> None:
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    default_cred = Path(__file__).resolve().parents[2] / "app" / "core" / "mvbl-492911-81f79d8de732.json"
    if default_cred.exists():
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(default_cred))


def _get_vision_client():
    global _VISION_CLIENT
    if _VISION_CLIENT is not None:
        return _VISION_CLIENT

    if vision is None:
        return None

    _ensure_google_credential_env()
    with _VISION_LOCK:
        if _VISION_CLIENT is None:
            try:
                _VISION_CLIENT = vision.ImageAnnotatorClient()
            except Exception:
                _VISION_CLIENT = None
    return _VISION_CLIENT


def _normalize_plate_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _extract_plate_candidate(raw_text: str) -> Optional[str]:
    cleaned = raw_text.upper().replace("\n", " ")
    patterns = [
        r"\b\d{2}[A-Z]\d?-?\d{3}\.?\d{2}\b",
        r"\b\d{2}[A-Z]-?\d{3,4}\b",
        r"\b\d{2}[A-Z]{1,2}\d{4,5}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            return _normalize_plate_text(match.group(0))
    return None


def _extract_refc_or_qr_candidate(raw_text: str) -> Optional[str]:
    cleaned = raw_text.upper().replace("\n", " ")
    refc = re.search(r"\bREFC[-_A-Z0-9]{2,}\b", cleaned)
    if refc:
        return refc.group(0)

    qr_like = re.search(r"\b[A-Z0-9]{8,}\b", cleaned)
    if qr_like:
        return qr_like.group(0)
    return None


class _BaseCameraHandler:
    def __init__(
        self,
        label: ctk.CTkLabel,
        on_detection: Optional[Callable[[Dict[str, object]], None]] = None,
    ):
        self.label = label
        self.running = False
        self._latest_frame = None
        self._frame_lock = threading.Lock()
        self._on_detection = on_detection
        self._emit_cache: Dict[str, float] = {}
        self._vision_interval = float(os.getenv("VISION_FRAME_INTERVAL_SECONDS", "1.4"))
        self._last_vision_ts = 0.0
        self._last_vision_plate = ""
        self._last_vision_code = ""
        self._last_plate_box: Optional[Tuple[int, int, int, int]] = None
        self._last_plate_conf = 0.0
        self._last_plate_source = ""
        self._last_plate_box_ts = 0.0
        self._plate_overlay_ttl = float(os.getenv("PLATE_OVERLAY_TTL_SECONDS", "2.2"))

    def stop(self):
        self.running = False

    def get_latest_frame_base64(self, jpeg_quality: int = 85) -> Optional[str]:
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            frame = self._latest_frame.copy()

        try:
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
            success, buffer = cv2.imencode(".jpg", frame, encode_params)
            if not success:
                return None
            return base64.b64encode(buffer.tobytes()).decode("utf-8")
        except Exception:
            return None

    def _emit_detection(self, detection_type: str, value: str, confidence: float, source: str) -> None:
        value = (value or "").strip()
        if not value:
            return

        key = f"{detection_type}:{value}:{source}"
        now = time.time()
        if now - self._emit_cache.get(key, 0.0) < 1.4:
            return
        self._emit_cache[key] = now

        if callable(self._on_detection):
            payload = {
                "type": detection_type,
                "value": value,
                "confidence": round(float(confidence), 2),
                "source": source,
            }
            self._on_detection(payload)

    def _draw_red_box(self, frame, x1: int, y1: int, x2: int, y2: int, text: str) -> None:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(
            frame,
            text,
            (x1, max(18, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    def _draw_top_text(self, frame, line: str, y: int) -> None:
        cv2.putText(
            frame,
            line,
            (10, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    def _bbox_from_vertices(self, vertices, frame_shape) -> Optional[Tuple[int, int, int, int]]:
        if not vertices:
            return None

        points = []
        for v in vertices:
            x = getattr(v, "x", None)
            y = getattr(v, "y", None)
            if x is None or y is None:
                continue
            points.append((int(x), int(y)))

        if not points:
            return None

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x1 = max(0, min(xs))
        y1 = max(0, min(ys))
        x2 = min(frame_shape[1] - 1, max(xs))
        y2 = min(frame_shape[0] - 1, max(ys))
        if x2 <= x1 or y2 <= y1:
            return None
        return (x1, y1, x2, y2)

    def _set_plate_overlay(
        self,
        plate_text: str,
        confidence: float,
        source: str,
        plate_box: Optional[Tuple[int, int, int, int]],
    ) -> None:
        if not plate_text:
            return

        self._last_plate_box = plate_box
        self._last_plate_conf = round(float(confidence), 1)
        self._last_plate_source = source
        self._last_plate_box_ts = time.time()

    def _draw_latest_plate_overlay(self, frame) -> None:
        if not self._last_vision_plate:
            return

        if time.time() - self._last_plate_box_ts > self._plate_overlay_ttl:
            return

        text = f"PLATE {self._last_plate_conf:.1f}%: {self._last_vision_plate}"
        if self._last_plate_box is not None:
            x1, y1, x2, y2 = self._last_plate_box
            self._draw_red_box(frame, x1, y1, x2, y2, text)
            return

        self._draw_top_text(frame, text, 78)

    def _run_yolo_overlay(self, frame) -> Tuple[float, Optional[Tuple[int, int, int, int]]]:
        best_plate_conf = 0.0
        best_plate_box = None
        model = _get_yolo_model()
        if model is None:
            return best_plate_conf, best_plate_box

        try:
            results = model(frame, verbose=False)
            if not results:
                return best_plate_conf, best_plate_box

            result = results[0]
            names = getattr(result, "names", {})
            boxes = getattr(result, "boxes", [])
            if isinstance(names, list):
                names = {idx: name for idx, name in enumerate(names)}

            for box in boxes:
                conf = float(box.conf[0]) * 100.0
                cls_idx = int(box.cls[0]) if box.cls is not None else -1
                class_name = str(names.get(cls_idx, "object")).lower()
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(frame.shape[1], x2)
                y2 = min(frame.shape[0], y2)
                if x2 <= x1 or y2 <= y1:
                    continue

                label = f"{class_name.upper()} {conf:.1f}%"
                self._draw_red_box(frame, x1, y1, x2, y2, label)

                if any(token in class_name for token in ("plate", "license", "lp")):
                    if conf > best_plate_conf:
                        best_plate_conf = conf
                        best_plate_box = (x1, y1, x2, y2)
        except Exception:
            pass

        return best_plate_conf, best_plate_box

    def _run_qr_refc_overlay(self, frame, emit_code: Optional[Callable[[str], None]]) -> None:
        if zbar_decode is None:
            return

        try:
            decoded = zbar_decode(frame)
        except Exception:
            decoded = []

        for item in decoded:
            code = item.data.decode("utf-8", errors="ignore").strip()
            if not code:
                continue

            points = item.polygon if getattr(item, "polygon", None) else None
            if points and len(points) >= 4:
                np_points = np.array([(pt.x, pt.y) for pt in points], dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [np_points], True, (0, 0, 255), 2)
                x, y = int(np_points[0][0][0]), int(np_points[0][0][1])
            else:
                rect = item.rect
                x, y, w, h = rect.left, rect.top, rect.width, rect.height
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

            detection_type = "refc" if "REFC" in code.upper() else "qr"
            cv2.putText(
                frame,
                f"{detection_type.upper()} 99.0%",
                (x, max(18, y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )
            self._emit_detection(detection_type, code, 99.0, "zbar")

            if callable(emit_code):
                emit_code(code)

    def _run_google_vision_extract(self, frame, yolo_plate_conf: float) -> None:
        now = time.time()
        if now - self._last_vision_ts < self._vision_interval:
            return
        self._last_vision_ts = now

        client = _get_vision_client()
        if client is None:
            return

        try:
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                return
            image = vision.Image(content=encoded.tobytes())
            context = vision.ImageContext(language_hints=["vi"])
            response = client.text_detection(image=image, image_context=context)
            texts = response.text_annotations
            if not texts:
                return

            raw = texts[0].description

            plate_bbox = None
            plate_candidate = None
            for annotation in texts[1:]:
                one_text = (annotation.description or "").strip()
                if not one_text:
                    continue

                parsed_plate = _extract_plate_candidate(one_text)
                if parsed_plate:
                    plate_candidate = parsed_plate
                    plate_bbox = self._bbox_from_vertices(
                        getattr(annotation.bounding_poly, "vertices", []),
                        frame.shape,
                    )
                    break

            if plate_candidate is None:
                plate_candidate = _extract_plate_candidate(raw)

            if plate_candidate and plate_bbox is None:
                candidate_norm = _normalize_plate_text(plate_candidate)
                matched_boxes = []
                for annotation in texts[1:]:
                    token = (annotation.description or "").strip()
                    token_norm = _normalize_plate_text(token)
                    if not token_norm:
                        continue

                    if token_norm in candidate_norm or candidate_norm in token_norm:
                        token_box = self._bbox_from_vertices(
                            getattr(annotation.bounding_poly, "vertices", []),
                            frame.shape,
                        )
                        if token_box is not None:
                            matched_boxes.append(token_box)

                if matched_boxes:
                    x1 = min(box[0] for box in matched_boxes)
                    y1 = min(box[1] for box in matched_boxes)
                    x2 = max(box[2] for box in matched_boxes)
                    y2 = max(box[3] for box in matched_boxes)
                    plate_bbox = (x1, y1, x2, y2)

            if plate_candidate:
                self._last_vision_plate = plate_candidate
                confidence = max(65.0, yolo_plate_conf) if yolo_plate_conf > 0 else 82.0
                self._emit_detection("plate", plate_candidate, confidence, "google_vision")
                self._set_plate_overlay(
                    plate_text=plate_candidate,
                    confidence=confidence,
                    source="google_vision",
                    plate_box=plate_bbox,
                )

            refc_or_qr = _extract_refc_or_qr_candidate(raw)
            if refc_or_qr:
                self._last_vision_code = refc_or_qr
                dtype = "refc" if refc_or_qr.upper().startswith("REFC") else "qr"
                self._emit_detection(dtype, refc_or_qr, 88.0, "google_vision")
        except Exception:
            return

    def _render_frame(self, frame, emit_code: Optional[Callable[[str], None]] = None) -> None:
        preview = frame.copy()
        yolo_plate_conf, yolo_plate_box = self._run_yolo_overlay(preview)
        self._run_qr_refc_overlay(preview, emit_code=emit_code)
        self._run_google_vision_extract(frame, yolo_plate_conf=yolo_plate_conf)

        if yolo_plate_box is not None and self._last_vision_plate:
            self._set_plate_overlay(
                plate_text=self._last_vision_plate,
                confidence=max(55.0, yolo_plate_conf),
                source="yolo+vision",
                plate_box=yolo_plate_box,
            )

        self._draw_latest_plate_overlay(preview)

        if self._last_vision_plate:
            self._draw_top_text(preview, f"VISION PLATE: {self._last_vision_plate}", 26)
        if self._last_vision_code:
            self._draw_top_text(preview, f"VISION REFC/QR: {self._last_vision_code}", 52)

        with self._frame_lock:
            self._latest_frame = preview.copy()

        rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        width = max(int(self.label.winfo_width() or 640), 320)
        height = max(int(self.label.winfo_height() or 360), 180)
        resized = pil_image.resize((width, height))
        ctk_image = ctk.CTkImage(light_image=resized, dark_image=resized, size=(width, height))
        self.label.after(0, self._update_label_image, ctk_image, "")

    def _show_error(self, text: str):
        self.label.after(0, self._update_label_image, None, text)

    def _update_label_image(self, ctk_image, text: str):
        if ctk_image is None:
            self.label.configure(image=None, text=text)
            self.label.image = None
            return
        self.label.configure(image=ctk_image, text=text)
        self.label.image = ctk_image


class CameraHandler:
    def __init__(
        self,
        label: ctk.CTkLabel,
        callback: Optional[Callable[[str], None]] = None,
        on_detection: Optional[Callable[[Dict[str, object]], None]] = None,
    ):
        self.base = _BaseCameraHandler(label, on_detection=on_detection)
        self.cap = None
        self.callback = callback
        self._last_code = ""
        self._last_emit_ts = 0.0

    def start(self, camera_id=0):
        if self.base.running:
            return
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            self.base._show_error("Khong mo duoc camera laptop")
            return
        self.base.running = True
        threading.Thread(target=self._update, daemon=True).start()

    def stop(self):
        self.base.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def get_latest_frame_base64(self, jpeg_quality: int = 85) -> Optional[str]:
        return self.base.get_latest_frame_base64(jpeg_quality=jpeg_quality)

    def _emit_code(self, code: str) -> None:
        if not callable(self.callback):
            return
        now = time.time()
        if code != self._last_code or (now - self._last_emit_ts) > 1.2:
            self._last_code = code
            self._last_emit_ts = now
            self.callback(code)

    def _update(self):
        while self.base.running:
            if self.cap is None:
                break

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            self.base._render_frame(frame, emit_code=self._emit_code)

        self.stop()


class IoTCameraHandler:
    def __init__(
        self,
        label: ctk.CTkLabel,
        capture_url: Optional[str] = None,
        on_detection: Optional[Callable[[Dict[str, object]], None]] = None,
    ):
        self.base = _BaseCameraHandler(label, on_detection=on_detection)
        self.capture_url = capture_url or os.getenv("ESP32_CAPTURE_URL", "http://192.168.81.61/capture")
        self.capture_timeout = float(os.getenv("ESP32_CAPTURE_TIMEOUT_SECONDS", "4"))
        self.refresh_interval = float(os.getenv("ESP32_REFRESH_SECONDS", "1.0"))

    def start(self):
        if self.base.running:
            return
        self.base.running = True
        threading.Thread(target=self._update, daemon=True).start()

    def stop(self):
        self.base.stop()

    def _update(self):
        while self.base.running:
            try:
                response = requests.get(self.capture_url, timeout=self.capture_timeout)
                response.raise_for_status()
                content = response.content
                if not content:
                    self.base._show_error("IoT camera khong tra ve hinh")
                    time.sleep(self.refresh_interval)
                    continue

                frame = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    self.base._show_error("IoT camera tra ve du lieu khong hop le")
                    time.sleep(self.refresh_interval)
                    continue

                self.base._render_frame(frame)
            except Exception:
                self.base._show_error("Khong ket noi duoc camera IoT")

            time.sleep(self.refresh_interval)
