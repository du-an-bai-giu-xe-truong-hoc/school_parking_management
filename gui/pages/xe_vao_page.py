# gui/pages/xe_vao_page.py
import customtkinter as ctk
from PIL import Image, ImageTk
from ..utils.camera import CameraHandler
from ..utils.api_client import ApiClient
from ..utils.hardware_controller import HardwareController
from ..styles import AppStyle

class XeVaoPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="transparent")
        self.main_app = main_app
        self.hardware = HardwareController()
        self.hardware.connect()

        self.grid_columnconfigure((0, 1), weight=1)

        # Lane A
        self._create_lane_frame(0, "LÀN XE VÀO A - THÔNG TIN XE", "Khu C", camera_id=0)
        # Lane B
        self._create_lane_frame(1, "LÀN XE VÀO B - THÔNG TIN XE", "Khu D", camera_id=1)

    def _create_lane_frame(self, col: int, title: str, khu: str, camera_id: int):
        frame = ctk.CTkFrame(self, corner_radius=12, fg_color=AppStyle.CARD_BG)
        frame.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(frame, text=title, font=AppStyle().subtitle, text_color=AppStyle.PRIMARY).pack(pady=(10, 5))

        # Camera
        cam_frame = ctk.CTkFrame(frame, height=240)
        cam_frame.pack(fill="x", padx=15, pady=5)
        cam_label = ctk.CTkLabel(cam_frame, text="📷 Camera đang chờ...", fg_color="#E2E8F0", height=220)
        cam_label.pack(fill="x", padx=10, pady=10)

        # Cận biển số
        closeup_label = ctk.CTkLabel(frame, text="Ảnh chụp cận biển số", font=("Helvetica", 13))
        closeup_label.pack(pady=5)

        # Camera handler
        camera = CameraHandler(cam_label, callback=lambda plate: self.on_plate_detected(plate, frame, khu))
        camera.start(camera_id=camera_id)

        # Thông tin xe
        self.info_frame = ctk.CTkFrame(frame, fg_color="#F8FAFC")
        self.info_frame.pack(fill="x", padx=15, pady=10)

        self.lbl_plate = ctk.CTkLabel(self.info_frame, text="Biển số: Chưa có", font=("Helvetica", 18, "bold"))
        self.lbl_plate.pack(pady=3)
        ctk.CTkLabel(self.info_frame, text=f"ID Thẻ SV: -").pack()
        ctk.CTkLabel(self.info_frame, text="Thời gian vào: -").pack()
        ctk.CTkLabel(self.info_frame, text=f"Vị trí đỗ: {khu}").pack()

        # Nút hành động
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="✅ Xác nhận & Mở Barrier", fg_color=AppStyle.SUCCESS, height=40,
                      command=lambda: self.confirm_entry(khu)).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="❌ Không cho qua", fg_color=AppStyle.DANGER, height=40).pack(side="left", padx=8)

    def on_plate_detected(self, plate: str, frame, khu: str):
        vehicle = ApiClient.get_vehicle_by_plate(plate)
        if vehicle:
            self.lbl_plate.configure(text=f"Biển số: {plate}")
            # Cập nhật các label khác...
        else:
            ctk.CTkMessagebox(title="Lỗi", message="Xe không tồn tại trong hệ thống!", icon="warning")

    def confirm_entry(self, khu: str):
        # Gọi API tạo transaction + mở barrier
        success = self.hardware.open_barrier("A" if "A" in khu else "B")
        if success:
            ctk.CTkMessagebox(title="Thành công", message=f"Đã mở barrier {khu}!", icon="check")
