# gui/utils/camera.py
import cv2
import threading
from PIL import Image, ImageTk
import customtkinter as ctk
from datetime import datetime

class CameraHandler:
    def __init__(self, label: ctk.CTkLabel, callback=None):
        self.label = label
        self.cap = None
        self.running = False
        self.callback = callback
        self.current_frame = None          # Lưu frame mới nhất để chụp ảnh biển số
        self.last_ocr_time = 0             # Tránh gọi OCR liên tục

    def start(self, source=0):
        """
        source có thể là:
          - int (0, 1...) → webcam laptop (demo)
          - str[](http://192.168.x.x:81/stream) → ESP32-CAM
        """
        if isinstance(source, str):
            print(f"🔗 Đang kết nối ESP32-CAM: {source}")
        else:
            print(f"📹 Đang dùng webcam local ID: {source}")

        self.cap = cv2.VideoCapture(source)
        self.running = True
        threading.Thread(target=self._update, daemon=True).start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame.copy()

                # Gọi OCR backend mỗi 2 giây (tự động quét biển số)
                import time
                if time.time() - self.last_ocr_time > 2 and self.callback:
                    self.last_ocr_time = time.time()
                    self.callback(frame)   # Truyền frame thô → backend sẽ OCR

                # Hiển thị stream live
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb).resize((640, 360))
                photo = ImageTk.PhotoImage(image=img)
                self.label.configure(image=photo)
                self.label.image = photo   # Giữ reference

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

    def get_current_frame(self):
        return self.current_frame
