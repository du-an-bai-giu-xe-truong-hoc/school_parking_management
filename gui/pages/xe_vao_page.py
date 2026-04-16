# gui/pages/xe_vao_page.py
import customtkinter as ctk
from ..utils.camera import CameraHandler
from ..utils.api_client import ApiClient
from ..utils.hardware_controller import HardwareController
from ..styles import AppStyle

class XeVaoPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.hardware = HardwareController()

        # 2 column
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Lane A
        self.frame_a = ctk.CTkFrame(self, corner_radius=12)
        self.frame_a.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self._create_lane(self.frame_a, "LÀN XE VÀO A", "Khu C")

        # Lane B
        self.frame_b = ctk.CTkFrame(self, corner_radius=12)
        self.frame_b.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")
        self._create_lane(self.frame_b, "LÀN XE VÀO B", "Khu D")

    def _create_lane(self, parent, title, khu):
        ctk.CTkLabel(parent, text=title, font=AppStyle().subtitle, text_color=AppStyle.PRIMARY).pack(pady=8)

        # Camera + biển số
        cam_frame = ctk.CTkFrame(parent)
        cam_frame.pack(pady=5, padx=10, fill="x")
        self.cam_label = ctk.CTkLabel(cam_frame, text="📷 Camera đang chờ...", height=220, fg_color="#E2E8F0")
        self.cam_label.pack(fill="x", padx=10)

        # Camera handler
        self.camera = CameraHandler(self.cam_label, callback=lambda p: self.on_plate_detected(p, parent))
        self.camera.start(camera_id=0)   # camera thật

        # Thông tin xe
        info_frame = ctk.CTkFrame(parent, fg_color=AppStyle.CARD_BG)
        info_frame.pack(pady=10, padx=15, fill="x")
        ctk.CTkLabel(info_frame, text="Biển số: Chưa có", font=("Helvetica", 18, "bold")).pack(pady=5)
        # ... các label khác (ID Thẻ SV, Thời gian vào, Vị trí đỗ Khu C...)

        # Nút
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="✅ Xác nhận & Mở Barrier", fg_color=AppStyle.SUCCESS,
                      command=lambda: self.open_barrier("A" if "A" in title else "B")).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="❌ Không cho qua", fg_color=AppStyle.DANGER).pack(side="left", padx=5)
