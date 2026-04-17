# gui/pages/xe_vao_page.py
import customtkinter as ctk
from PIL import Image, ImageTk
from datetime import datetime
import pytz  # pip install pytz (nếu chưa có)

from utils.camera import CameraHandler
from utils.api_client import ApiClient
from utils.hardware_controller import HardwareController
from styles import AppStyle


class XeVaoPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="transparent")
        self.main_app = main_app
        self.hardware = HardwareController()
# self.hardware.connect()                    # cũ
self.hardware.connect(http_url="http://192.168.1.184")   # ←←← THAY IP ESP32 CỦA BẠN

        # Lưu lịch sử xe vào
        self.history = []

        # Tạo giao diện chỉ 1 lane
        self._create_single_lane()

    def _create_single_lane(self):
        # Frame chính
        main_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=AppStyle.CARD_BG)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(main_frame, text="LÀN XE VÀO - THÔNG TIN XE",
                     font=AppStyle.SUBTITLE_FONT, text_color=AppStyle.PRIMARY).pack(pady=(12, 8))

        # ==================== CAMERA LIVE ====================
        cam_frame = ctk.CTkFrame(main_frame, height=300, fg_color="#1E2937")
        cam_frame.pack(fill="x", padx=15, pady=8)
        self.cam_label = ctk.CTkLabel(cam_frame, text="📷 Đang kết nối camera ESP32-CAM...",
                                      fg_color="#1E2937", text_color="white", height=280)
        self.cam_label.pack(fill="both", expand=True, padx=10, pady=10)

        # ==================== ẢNH CHỤP BIỂN SỐ ====================
        self.closeup_label = ctk.CTkLabel(main_frame, text="Ảnh chụp cận biển số",
                                          font=("Helvetica", 13, "bold"))
        self.closeup_label.pack(pady=(10, 5))

        self.plate_photo_label = ctk.CTkLabel(main_frame, text="Chưa có ảnh", height=140,
                                              fg_color="#E2E8F0", corner_radius=8)
        self.plate_photo_label.pack(fill="x", padx=40, pady=5)

        # ==================== THÔNG TIN XE ====================
        info_frame = ctk.CTkFrame(main_frame, fg_color="#F8FAFC", corner_radius=8)
        info_frame.pack(fill="x", padx=30, pady=15)

        self.lbl_plate = ctk.CTkLabel(info_frame, text="Biển số: Chưa có",
                                      font=("Helvetica", 20, "bold"), text_color="#1E40AF")
        self.lbl_plate.pack(pady=4)

        self.lbl_id = ctk.CTkLabel(info_frame, text="ID Thẻ SV: -", font=("Helvetica", 14))
        self.lbl_id.pack(pady=2)

        self.lbl_time = ctk.CTkLabel(info_frame, text="Thời gian vào: -", font=("Helvetica", 14))
        self.lbl_time.pack(pady=2)

        self.lbl_khu = ctk.CTkLabel(info_frame, text="Vị trí đỗ: Khu C", font=("Helvetica", 14))
        self.lbl_khu.pack(pady=2)

        # ==================== NÚT THỦ CÔNG ====================
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        self.btn_confirm = ctk.CTkButton(
            btn_frame, text="✅ Xác nhận & Mở Barrier",
            fg_color=AppStyle.SUCCESS, height=48, font=("Helvetica", 16, "bold"),
            command=self.confirm_entry_manual
        )
        self.btn_confirm.pack(side="left", padx=12)

        self.btn_reject = ctk.CTkButton(
            btn_frame, text="❌ Không cho qua",
            fg_color=AppStyle.DANGER, height=48, font=("Helvetica", 16, "bold"),
            command=self.reject_entry
        )
        self.btn_reject.pack(side="left", padx=12)

        # ==================== BẢNG LỊCH SỬ ====================
        history_title = ctk.CTkLabel(main_frame, text="📋 LỊCH SỬ XE VÀO",
                                     font=("Helvetica", 16, "bold"))
        history_title.pack(pady=(20, 5), anchor="w", padx=30)

        self.history_scroll = ctk.CTkScrollableFrame(main_frame, height=220)
        self.history_scroll.pack(fill="x", padx=30, pady=5)

        # Khởi động camera (thay IP ESP32-CAM của bạn vào đây)
        self.camera = CameraHandler(self.cam_label, callback=self.on_frame_received)
        # === THAY ĐỔI IP NÀY THEO ESP32-CAM CỦA BẠN ===
        esp32_stream_url = "http://192.168.1.184:81/stream"   # ←←←← THAY IP NÀY
        self.camera.start(source=esp32_stream_url)   # hoặc 0 để test webcam

    def on_frame_received(self, frame):
        """Nhận frame từ camera → gọi backend OCR + logic tự động"""
        # Gọi API OCR biển số (bạn đã có endpoint này ở backend)
        result = ApiClient.ocr_plate(frame)   # Giả sử bạn đã implement hàm này

        if result and result.get("plate"):
            plate = result["plate"]
            self.lbl_plate.configure(text=f"Biển số: {plate}")

            # Lưu ảnh biển số
            self._show_plate_image(frame)

            # Tự động đối chiếu database
            vehicle = ApiClient.get_vehicle_by_plate(plate)
            if vehicle:
                self._update_vehicle_info(vehicle)
                self._auto_open_barrier(plate, vehicle)
            else:
                # Xe chưa có trong DB → hiển thị cảnh báo
                self.lbl_plate.configure(text_color="red")

    def _show_plate_image(self, frame):
        """Hiển thị ảnh chụp biển số"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((380, 140))
        photo = ImageTk.PhotoImage(image=img)
        self.plate_photo_label.configure(image=photo)
        self.plate_photo_label.image = photo

    def _update_vehicle_info(self, vehicle):
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.now(vn_tz).strftime("%d/%m/%Y %H:%M:%S")

        self.lbl_id.configure(text=f"ID Thẻ SV: {vehicle.get('id_the', '-')}")
        self.lbl_time.configure(text=f"Thời gian vào: {now}")
        self.lbl_khu.configure(text=f"Vị trí đỗ: Khu C")

    def _auto_open_barrier(self, plate: str, vehicle):
        """Tự động mở barrier nếu xe hợp lệ"""
        success = self.hardware.open_barrier("A")   # Lane A
        if success:
            self.add_to_history(plate, vehicle.get('id_the', '-'), "✅ ĐÃ VÀO")
            ctk.CTkMessagebox(title="Tự động", message=f"Xe {plate} đã được mở barrier!", icon="check")

    def confirm_entry_manual(self):
        """Nút thủ công mở barrier"""
        success = self.hardware.open_barrier("A")
        if success:
            self.add_to_history("MANUAL", "-", "✅ Mở thủ công")
            ctk.CTkMessagebox(title="Thành công", message="Đã mở barrier!", icon="check")

    def reject_entry(self):
        """Không cho qua"""
        self.add_to_history("REJECT", "-", "❌ Không cho qua")
        ctk.CTkMessagebox(title="Từ chối", message="Xe không được vào!", icon="warning")

    def add_to_history(self, plate: str, id_the: str, status: str):
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        time_str = datetime.now(vn_tz).strftime("%H:%M:%S")

        self.history.insert(0, {"time": time_str, "plate": plate, "id": id_the, "status": status})

        # Xóa hết widget cũ
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        # Tạo lại bảng lịch sử
        for entry in self.history[:10]:   # chỉ hiển thị 10 dòng gần nhất
            row = ctk.CTkFrame(self.history_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2, padx=5)

            ctk.CTkLabel(row, text=entry["time"], width=80).pack(side="left")
            ctk.CTkLabel(row, text=entry["plate"], width=120).pack(side="left")
            ctk.CTkLabel(row, text=entry["id"], width=100).pack(side="left")
            ctk.CTkLabel(row, text=entry["status"], text_color="green" if "✅" in entry["status"] else "red").pack(side="right")

    def destroy(self):
        """Dọn dẹp khi đóng trang"""
        if hasattr(self, 'camera'):
            self.camera.stop()
        super().destroy()
