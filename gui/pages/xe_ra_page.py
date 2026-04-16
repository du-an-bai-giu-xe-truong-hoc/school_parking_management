# gui/pages/xe_ra_page.py
import customtkinter as ctk
from ..styles import AppStyle
from ..utils.api_client import ApiClient
from ..utils.hardware_controller import HardwareController

class XeRaPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="transparent")
        self.hardware = HardwareController()

        # Banner đỏ cảnh báo (2 cái song song)
        self._create_warning_banner("77A-078.34", "Khu A", "gray_car.jpg")   # thay bằng ảnh thật
        self._create_warning_banner("77A-364.24", "Khu B", "silver_car.jpg")

        # So sánh biển số
        compare_frame = ctk.CTkFrame(self, fg_color=AppStyle.CARD_BG)
        compare_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(compare_frame, text="SO SÁNH 2 ID KHÁC NHAU - PHÂN TÍCH RA", font=("Helvetica", 16, "bold")).pack(pady=8)

        # Bảng lịch sử (dùng CTkTable hoặc Treeview)
        # ... (bạn có thể dùng ttk.Treeview hoặc pandas + CTk)

        # Nút hành động
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="✅ Xác nhận mở barrier", fg_color=AppStyle.SUCCESS,
                      command=self.open_barrier).pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="🚨 Gửi cảnh báo", fg_color=AppStyle.DANGER).pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="❌ Không phải xe chính chủ", fg_color="#64748B").pack(side="left", padx=15)

    def _create_warning_banner(self, plate: str, khu: str, car_image: str):
        banner = ctk.CTkFrame(self, fg_color=AppStyle.DANGER, corner_radius=8)
        banner.pack(fill="x", padx=15, pady=8)
        ctk.CTkLabel(banner, text=f"CẢNH BÁO KHÓA XE - Biển số: {plate}", font=("Helvetica", 18, "bold"),
                     text_color="white").pack(pady=8)
        ctk.CTkLabel(banner, text=f"Vị trí đỗ: {khu}", text_color="white").pack()

    def open_barrier(self):
        self.hardware.open_barrier()
        ctk.CTkMessagebox(title="Thành công", message="Đã mở barrier!", icon="check")
