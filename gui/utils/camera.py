import base64
import os
import threading
import time
from typing import Optional

import customtkinter as ctk
import cv2
import numpy as np
import requests
from PIL import Image

try:
    from pyzbar.pyzbar import decode as zbar_decode
except Exception:
    zbar_decode = None

class _BaseCameraHandler:
    def __init__(self, label: ctk.CTkLabel):
        self.label = label
        self.running = False
        self._latest_frame = None
        self._frame_lock = threading.Lock()

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

    def _push_frame(self, frame, fallback_text: str = ""):
        with self._frame_lock:
            self._latest_frame = frame.copy()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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
    def __init__(self, label: ctk.CTkLabel, callback=None):
        self.base = _BaseCameraHandler(label)
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

    def _update(self):
        while self.base.running:
            if self.cap is None:
                break

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            if zbar_decode is not None:
                for barcode in zbar_decode(frame):
                    code = barcode.data.decode("utf-8").strip()
                    if not code:
                        continue
                    now = time.time()
                    if code != self._last_code or (now - self._last_emit_ts) > 2.0:
                        self._last_code = code
                        self._last_emit_ts = now
                        if self.callback:
                            self.callback(code)

            self.base._push_frame(frame)

        self.stop()


class IoTCameraHandler:
    def __init__(self, label: ctk.CTkLabel, capture_url: Optional[str] = None):
        self.base = _BaseCameraHandler(label)
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
                self.base._push_frame(frame)
            except Exception:
                self.base._show_error("Khong ket noi duoc camera IoT")

            time.sleep(self.refresh_interval)
import cv2
import requests
from PIL import Image

try:
    from pyzbar.pyzbar import decode as zbar_decode
except Exception:
    zbar_decode = None


class _BaseCameraHandler:
    def __init__(self, label: ctk.CTkLabel):
        self.label = label
        self.running = False
        self._latest_frame = None
        self._frame_lock = threading.Lock()

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

    def _push_frame(self, frame, fallback_text: str = ""):
        with self._frame_lock:
            self._latest_frame = frame.copy()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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
    def __init__(self, label: ctk.CTkLabel, callback=None):
        self.base = _BaseCameraHandler(label)
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

    def _update(self):
        while self.base.running:
            if self.cap is None:
                break

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            if zbar_decode is not None:
                for barcode in zbar_decode(frame):
                    code = barcode.data.decode("utf-8").strip()
                    if not code:
                        continue
                    now = time.time()
                    if code != self._last_code or (now - self._last_emit_ts) > 2.0:
                        self._last_code = code
                        self._last_emit_ts = now
                        if self.callback:
                            self.callback(code)

            self.base._push_frame(frame)

        self.stop()


class IoTCameraHandler:
    def __init__(self, label: ctk.CTkLabel, capture_url: Optional[str] = None):
        self.base = _BaseCameraHandler(label)
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

                frame = cv2.imdecode(np_from_bytes(content), cv2.IMREAD_COLOR)
                if frame is None:
                    self.base._show_error("IoT camera tra ve du lieu khong hop le")
                    time.sleep(self.refresh_interval)
                    continue
                self.base._push_frame(frame)
            except Exception:
                self.base._show_error("Khong ket noi duoc camera IoT")

            time.sleep(self.refresh_interval)


def np_from_bytes(image_bytes: bytes):
    import numpy as np

    return np.frombuffer(image_bytes, dtype=np.uint8)
