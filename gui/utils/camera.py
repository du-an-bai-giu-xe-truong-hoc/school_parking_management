import base64
import importlib
import os
import re
import threading
import time
import warnings
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

import customtkinter as ctk
import cv2
import numpy as np
import requests
from PIL import Image

try:
    from pyzbar.pyzbar import ZBarSymbol, decode as zbar_decode
except Exception:
    ZBarSymbol = None
    zbar_decode = None

try:
    warnings.filterwarnings(
        "ignore",
        message=r"You are using a Python version .* end of life.*",
        category=FutureWarning,
        module=r"google\.api_core\._python_version_support",
    )
    from google.cloud import vision
except Exception:
    vision = None

_YOLO_CLASS = None
_YOLO_IMPORT_ATTEMPTED = False


_YOLO_LOCK = threading.Lock()
_YOLO_MODEL = None

_VISION_LOCK = threading.Lock()
_VISION_CLIENT = None

_QR_ONLY_DECODE = os.getenv("ZBAR_QR_ONLY", "1").strip().lower() not in {"0", "false", "no"}
_DEFAULT_ESP32_BASE_URL = os.getenv("ESP32_BASE_URL", "http://192.168.81.61").strip()


def _resolve_capture_url() -> str:
    use_backend_proxy = os.getenv("ESP32_USE_BACKEND_PROXY", "1").strip().lower() not in {"0", "false", "no"}
    if use_backend_proxy:
        backend = (os.getenv("FASTAPI_URL") or "http://localhost:8000").rstrip("/")
        prefix = (os.getenv("FASTAPI_PREFIX") or "/api").strip()
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"
        return f"{backend}{prefix}/camera/esp32/frame"

    explicit = (os.getenv("ESP32_CAPTURE_URL") or "").strip()
    if explicit:
        if explicit.startswith(("http://", "https://")):
            return explicit
        return f"http://{explicit}"

    esp32_ip = (os.getenv("ESP32_IP") or "192.168.81.61").strip()
    return f"http://{esp32_ip}/capture"


def _build_capture_candidates(raw_url: str) -> list[str]:
    normalized = (raw_url or "").strip()
    if not normalized:
        normalized = _DEFAULT_ESP32_BASE_URL
    if not normalized.startswith(("http://", "https://")):
        normalized = f"http://{normalized}"

    parsed = urlparse(normalized)
    if not parsed.netloc:
        return [normalized]

    base = f"{parsed.scheme}://{parsed.netloc}"
    path = (parsed.path or "").strip()

    candidates: list[str] = []
    fallback_base = base
    if path and path != "/":
        candidates.append(f"{base}{path}")
        # Neu dang dung API/proxy path, van them fallback truc tiep toi ESP32
        # de man hinh IoT van hien thi anh khi backend tam thoi chua chay.
        if path.lower().startswith("/api/"):
            esp32_ip = (os.getenv("ESP32_IP") or "192.168.81.61").strip()
            ip_fallback_base = f"http://{esp32_ip}"
            # Uu tien endpoint latest theo ESP32_IP de co hinh nhanh nhat.
            candidates.append(f"{ip_fallback_base}/latest")

            esp32_direct = (os.getenv("ESP32_CAPTURE_URL") or "").strip()
            if esp32_direct:
                if not esp32_direct.startswith(("http://", "https://")):
                    esp32_direct = f"http://{esp32_direct}"
                candidates.append(esp32_direct)
                parsed_direct = urlparse(esp32_direct)
                if parsed_direct.netloc:
                    fallback_base = f"{parsed_direct.scheme}://{parsed_direct.netloc}"
            else:
                fallback_base = f"http://{esp32_ip}"

            # Luon them fallback theo ESP32_IP de tranh truong hop ESP32_CAPTURE_URL cu/khong dung.
            if fallback_base != ip_fallback_base:
                candidates.append(f"{ip_fallback_base}/latest")
                candidates.append(f"{ip_fallback_base}/capture")
    else:
        preferred_path = (os.getenv("ESP32_CAPTURE_PATH") or "/capture").strip()
        if not preferred_path.startswith("/"):
            preferred_path = f"/{preferred_path}"
        candidates.append(f"{base}{preferred_path}")

    # Fallback cho các firmware ESP32-CAM phổ biến.
    for fallback_path in ("/latest", "/cam-hi.jpg", "/capture", "/"):
        candidates.append(f"{fallback_base}{fallback_path}")

    unique: list[str] = []
    seen = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _get_yolo_model():
    global _YOLO_MODEL, _YOLO_CLASS, _YOLO_IMPORT_ATTEMPTED
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL

    if not _YOLO_IMPORT_ATTEMPTED:
        _YOLO_IMPORT_ATTEMPTED = True
        try:
            module = importlib.import_module("ultralytics")
            _YOLO_CLASS = getattr(module, "YOLO", None)
        except Exception:
            _YOLO_CLASS = None

    if _YOLO_CLASS is None:
        return None

    model_path = os.getenv("YOLO_PLATE_MODEL_PATH", "ai_modules/best.pt")
    model_file = Path(model_path)
    if not model_file.exists():
        return None

    with _YOLO_LOCK:
        if _YOLO_MODEL is None:
            try:
                _YOLO_MODEL = _YOLO_CLASS(str(model_file))
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


def _extract_general_text_candidate(raw_text: str) -> Optional[str]:
    cleaned = raw_text.upper().replace("\n", " ")
    token = re.search(r"\b[A-Z0-9\-]{6,}\b", cleaned)
    if token:
        return token.group(0)
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
            # Decode QR only by default to avoid native zbar PDF417 assertion noise.
            if _QR_ONLY_DECODE and ZBarSymbol is not None:
                decoded = zbar_decode(frame, symbols=[ZBarSymbol.QRCODE])
            else:
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
            else:
                # Fallback: emit generic OCR text so UI can auto-fill barcode field.
                text_candidate = _extract_general_text_candidate(raw)
                if text_candidate:
                    self._last_vision_code = text_candidate
                    self._emit_detection("text", text_candidate, 76.0, "google_vision")
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
        # Respect configured label size first so preview frame stays fixed in the UI.
        configured_width = int(self.label.cget("width") or 0)
        configured_height = int(self.label.cget("height") or 0)
        width = max(configured_width, 320) if configured_width > 1 else max(int(self.label.winfo_width() or 640), 320)
        height = max(configured_height, 180) if configured_height > 1 else max(int(self.label.winfo_height() or 360), 180)
        resized = pil_image.resize((width, height))
        ctk_image = ctk.CTkImage(light_image=resized, dark_image=resized, size=(width, height))
        self._safe_after_update(ctk_image, "")

    def _show_error(self, text: str):
        self._safe_after_update(None, text)

    def _safe_after_update(self, ctk_image, text: str) -> None:
        try:
            self.label.after(0, self._update_label_image, ctk_image, text)
        except Exception:
            # Widget/event-loop may already be destroyed while worker thread is shutting down.
            return

    def _update_label_image(self, ctk_image, text: str):
        try:
            if ctk_image is None:
                self.label.configure(image=None, text=text)
                self.label.image = None
                return
            self.label.configure(image=ctk_image, text=text)
            self.label.image = ctk_image
        except Exception:
            return


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

        if os.name == "nt":
            # Prefer DirectShow on Windows to avoid repeated MSMF grab warnings.
            self.cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = cv2.VideoCapture(camera_id)
        else:
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
        self.capture_url = capture_url or _resolve_capture_url()
        self.capture_candidates = _build_capture_candidates(self.capture_url)
        self.status_candidates = self._build_status_candidates()
        self.capture_timeout = float(os.getenv("ESP32_CAPTURE_TIMEOUT_SECONDS", "4"))
        self.refresh_interval = float(os.getenv("ESP32_REFRESH_SECONDS", "1.0"))
        self._last_ir_state = False
        self._last_ir_poll_ts = 0.0
        self.ir_poll_interval = float(os.getenv("ESP32_IR_POLL_SECONDS", "0.45"))

    def _build_status_candidates(self) -> list[str]:
        candidates: list[str] = []
        seen = set()

        def _add(item: str):
            if item and item not in seen:
                seen.add(item)
                candidates.append(item)

        for candidate in self.capture_candidates:
            parsed = urlparse(candidate)
            if not parsed.netloc:
                continue
            base = f"{parsed.scheme}://{parsed.netloc}"
            path = (parsed.path or "").strip()
            if "/api/camera/esp32/" in path:
                _add(f"{base}/api/camera/esp32/status")
            _add(f"{base}/status")

        parsed_main = urlparse(self.capture_url)
        if parsed_main.netloc:
            base = f"{parsed_main.scheme}://{parsed_main.netloc}"
            path = (parsed_main.path or "").strip()
            if "/api/camera/esp32/" in path:
                _add(f"{base}/api/camera/esp32/status")

        return candidates

    @staticmethod
    def _extract_ir_state(payload: object) -> Optional[bool]:
        if isinstance(payload, dict):
            nested = payload.get("status")
            if isinstance(nested, dict):
                nested_state = IoTCameraHandler._extract_ir_state(nested)
                if nested_state is not None:
                    return nested_state

            for key in ("car_present", "ir", "ir_state", "ir_sensor", "ir_detected", "triggered", "motion"):
                if key in payload:
                    value = payload.get(key)
                    if isinstance(value, bool):
                        return value
                    if isinstance(value, (int, float)):
                        return int(value) == 1
                    if isinstance(value, str):
                        return value.strip().lower() in {"1", "true", "on", "active", "detected"}
        return None

    def _poll_ir_trigger(self) -> None:
        now = time.time()
        if (now - self._last_ir_poll_ts) < self.ir_poll_interval:
            return
        self._last_ir_poll_ts = now

        current_state: Optional[bool] = None
        for status_url in self.status_candidates:
            try:
                response = requests.get(status_url, timeout=min(self.capture_timeout, 2.5))
                response.raise_for_status()
                current_state = self._extract_ir_state(response.json())
                if current_state is not None:
                    break
            except Exception:
                continue

        if current_state is None:
            return

        # Rising edge only: avoid repeated UI resets while sensor keeps high state.
        if current_state and (not self._last_ir_state):
            self.base._emit_detection("ir", "triggered", 100.0, "esp32_status")

        self._last_ir_state = current_state

    def _fetch_iot_frame(self):
        for idx, candidate in enumerate(self.capture_candidates):
            try:
                response = requests.get(candidate, timeout=self.capture_timeout)
                response.raise_for_status()
                content = response.content or b""
                if not content:
                    continue

                content_type = (response.headers.get("Content-Type") or "").lower()
                is_image = "image" in content_type or content.startswith(b"\xff\xd8")
                if not is_image:
                    continue

                frame = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                # Đưa endpoint đang hoạt động lên đầu để giảm độ trễ cho các lần sau.
                if idx > 0:
                    self.capture_candidates.insert(0, self.capture_candidates.pop(idx))

                return frame
            except Exception:
                continue

        return None

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
                self._poll_ir_trigger()
                frame = self._fetch_iot_frame()
                if frame is None:
                    shown_target = self.capture_candidates[0] if self.capture_candidates else self.capture_url
                    self.base._show_error(
                        (
                            f"Khong co hinh IoT camera.\n"
                            f"Dang thu: {shown_target}\n"
                            "Hay chay run_api.ps1 (neu dung backend proxy) "
                            "hoac tat ESP32_USE_BACKEND_PROXY de lay truc tiep tu ESP32"
                        )
                    )
                    time.sleep(self.refresh_interval)
                    continue

                self.base._render_frame(frame)
            except Exception:
                self.base._show_error("Khong ket noi duoc camera IoT")

            time.sleep(self.refresh_interval)
