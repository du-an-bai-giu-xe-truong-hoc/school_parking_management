# gui/utils/camera.py
import cv2
import threading
from pyzbar.pyzbar import decode
from PIL import Image, ImageTk
import customtkinter as ctk

class CameraHandler:
    def __init__(self, label: ctk.CTkLabel, callback=None):
        self.label = label
        self.cap = None
        self.running = False
        self.callback = callback

    def start(self, camera_id=0):
        self.cap = cv2.VideoCapture(camera_id)
        self.running = True
        threading.Thread(target=self._update, daemon=True).start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Quét barcode
                for barcode in decode(frame):
                    plate = barcode.data.decode("utf-8").strip()
                    if self.callback:
                        self.callback(plate)
                # Hiển thị
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb).resize((640, 360))
                photo = ImageTk.PhotoImage(image=img)
                self.label.configure(image=photo)
                self.label.image = photo
