# gui/pages/xe_ra_page.py
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
from datetime import datetime
import pytz

from utils.camera import CameraHandler
from utils.api_client import ApiClient
from utils.hardware_controller import HardwareController
from styles import AppStyle


class XeRaPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="transparent")
        self.main_app = main_app
        self.hardware = HardwareController()
# self.hardware.connect()                    # cũ
self.hardware.connect(http_url="http://192.168.1.184")   # ←←← THAY IP ESP32 CỦA BẠN
        

        # Lưu lịch sử xe ra
        self.history = []

        # Trạng thái khóa xe (mặc định TẮT → xanh)
        self.is_locked = False

        self._create_single_lane()

    def _create_single_lane(self):
        main_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=AppStyle.CARD_BG)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Tiêu đề
        ctk.CTkLabel(main_frame, text="LÀN XE RA - THÔNG TIN XE",
                     font=AppStyle.SUBTITLE_FONT, text_color=AppStyle.PRIMARY).pack(pady=(12, 8))

        # ==================== BANNER CẢNH BÁO KHÓA XE ====================
        self.banner_label = ctk.CTkLabel(main_frame, text="", height=40, font=("Helvetica", 16, "bold"))
        self.banner_label.pack(fill="x", padx=15, pady=(0, 10))
        self._update_lock_banner()

        # ==================== CAMERA LIVE ====================
        cam_frame = ctk.CTkFrame(main_frame, height=300, fg_color="#1E2937")
        cam_frame.pack(fill="x", padx=15, pady=8)
        self.cam_label = ctk.CTkLabel(cam_frame, text="📷 Đang kết nối camera ESP32-CAM...",
                                      fg_color="#1E2937", text_color="white", height=280)
        self.cam_label.pack(fill="both", expand=True, padx=10, pady=10)

        # ==================== ẢNH CHỤP BIỂN SỐ LÚC RA ====================
        self.closeup_label = ctk.CTkLabel(main_frame, text="Ảnh chụp cận biển số lúc ra",
                                          font=("Helvetica", 13, "bold"))
        self.closeup_label.pack(pady=(10, 5))

        self.plate_photo_label = ctk.CTkLabel(main_frame, text="Chưa có ảnh", height=140,
                                              fg_color="#E2E8F0", corner_radius=8)
        self.plate_photo_label.pack(fill="x", padx=40, pady=5)

        # ==================== KẾT QUẢ KIỂM TRA ====================
        self.result_frame = ctk.CTkFrame(main_frame, fg_color="#F8FAFC", corner_radius=8)
        self.result_frame.pack(fill="x", padx=30, pady=10)

        self.lbl_plate = ctk.CTkLabel(self.result_frame, text="Biển số: Chưa có",
                                      font=("Helvetica", 20, "bold"))
        self.lbl_plate.pack(pady=4)

        self.lbl_check = ctk.CTkLabel(self.result_frame, text="", font=("Helvetica", 18, "bold"))
        self.lbl_check.pack(pady=6)

        self.lbl_time_out = ctk.CTkLabel(self.result_frame, text="Thời gian ra: -", font=("Helvetica", 14))
        self.lbl_time_out.pack(pady=2)

        self.lbl_time_in = ctk.CTkLabel(self.result_frame, text="Thời gian vào: -", font=("Helvetica", 14))
        self.lbl_time_in.pack(pady=2)

        # ==================== NÚT THỦ CÔNG ====================
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="🚪 Mở Cổng", fg_color=AppStyle.SUCCESS, height=48,
                      font=("Helvetica", 16, "bold"), command=self.open_gate_manual).pack(side="left", padx=12)

        ctk.CTkButton(btn_frame, text="🚪 Đóng Cổng", fg_color=AppStyle.DANGER, height=48,
                      font=("Helvetica", 16, "bold"), command=self.close_gate_manual).pack(side="left", padx=12)

        # ==================== LỊCH SỬ GIAO DỊCH ====================
        history_title = ctk.CTkLabel(main_frame, text="📋 LỊCH SỬ XE RA (Vào - Ra)",
                                     font=("Helvetica", 16, "bold"))
        history_title.pack(pady=(20, 5), anchor="w", padx=30)

        self.history_scroll = ctk.CTkScrollableFrame(main_frame, height=220)
        self.history_scroll.pack(fill="x", padx=30, pady=5)

        # Khởi động camera ESP32-CAM (thay IP của bạn)
        self.camera = CameraHandler(self.cam_label, callback=self.on_frame_received)
        esp32_stream_url = "http://192.168.1.184:81/stream"   # ←←← THAY IP ESP32-CAM CỦA BẠN
        self.camera.start(source=esp32_stream_url)

    def _update_lock_banner(self):
        """Cập nhật banner đỏ/xanh cảnh báo khóa xe"""
        if self.is_locked:
            self.banner_label.configure(text="⚠️ CẢNH BÁO KHÓA XE - Xe đang bị khóa!", fg_color="#EF4444", text_color="white")
        else:
            self.banner_label.configure(text="✅ Xe không bị khóa - Có thể ra", fg_color="#10B981", text_color="white")

    def on_frame_received(self, frame):
        """Tự động OCR biển số + kiểm tra xe"""
        result = ApiClient.ocr_plate(frame)   # Gọi backend OCR
        if not result or not result.get("plate"):
            return

        plate = result["plate"]
        self.lbl_plate.configure(text=f"Biển số: {plate}")

        # Lưu ảnh biển số lúc ra
        self._show_plate_image(frame)

        # Giả lập kiểm tra xe (mock data - sau thay bằng API thật)
        vehicle = ApiClient.get_vehicle_by_plate(plate)   # Hoặc mock data
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.now(vn_tz).strftime("%d/%m/%Y %H:%M:%S")

        if vehicle:
            # Xe hợp lệ
            self.lbl_check.configure(text="✅ ĐÚNG XE", text_color="#10B981")
            self.lbl_time_out.configure(text=f"Thời gian ra: {now}")
            self.lbl_time_in.configure(text=f"Thời gian vào: 16/04/2026 08:15:22")  # mock
            self.add_to_history(plate, "✅ Ra thành công")
            # Tự động mở cổng nếu không bị khóa
            if not self.is_locked:
                self.hardware.open_barrier("A")
        else:
            # Xe sai / không tồn tại
            self.lbl_check.configure(text="❌ SAI XE", text_color="#EF4444")
            self.lbl_time_out.configure(text=f"Thời gian ra: {now}")
            self.add_to_history(plate, "❌ Sai xe / Không cho ra")

    def _show_plate_image(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((380, 140))
        photo = ImageTk.PhotoImage(image=img)
        self.plate_photo_label.configure(image=photo)
        self.plate_photo_label.image = photo

    def open_gate_manual(self):
        success = self.hardware.open_barrier("A")
        if success:
            self.add_to_history("MANUAL", "🚪 Mở thủ công")
            ctk.CTkMessagebox(title="Thành công", message="Đã mở cổng!", icon="check")

    def close_gate_manual(self):
        success = self.hardware.close_barrier("A")   # Giả sử HardwareController có hàm này
        if success:
            ctk.CTkMessagebox(title="Thành công", message="Đã đóng cổng!", icon="check")

    def add_to_history(self, plate: str, status: str):
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        time_str = datetime.now(vn_tz).strftime("%H:%M:%S")

        self.history.insert(0, {"time_out": time_str, "plate": plate, "time_in": "08:15", "status": status})

        # Xóa widget cũ
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        for entry in self.history[:8]:
            row = ctk.CTkFrame(self.history_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2, padx=5)

            ctk.CTkLabel(row, text=entry["time_out"], width=80).pack(side="left")
            ctk.CTkLabel(row, text=entry["plate"], width=130).pack(side="left")
            ctk.CTkLabel(row, text=entry["time_in"], width=80).pack(side="left")
            ctk.CTkLabel(row, text=entry["status"], text_color="green" if "✅" in entry["status"] else "red").pack(side="right")

    def destroy(self):
        if hasattr(self, 'camera'):
            self.camera.stop()
        super().destroy()
