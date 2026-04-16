# gui/pages/xe_ra_page.py
import customtkinter as ctk
from styles import AppStyle
from utils.api_client import ApiClient
from utils.helpers import Helper
from utils.hardware_controller import HardwareController

class XeRaPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="#0F172A")
        self.main_app = main_app
        self.hardware = HardwareController()
        self.current_plate = None

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Cảnh báo đỏ
        self.warning_frame = ctk.CTkFrame(self, fg_color=AppStyle.DANGER, height=50)
        self.warning_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.warning_label = ctk.CTkLabel(self.warning_frame, text="🚨 CẢNH BÁO KHÓA XE - Biển số: ________", 
                                          text_color="white", font=ctk.CTkFont(size=16, weight="bold"))
        self.warning_label.pack(pady=10)

        ctk.CTkLabel(self, text="Xe Ra - So sánh & Xử lý", font=ctk.CTkFont(size=20, weight="bold")).grid(row=1, column=0, columnspan=2, pady=10)

        self.create_camera_comparison()
        self.create_comparison_table()
        self.create_action_buttons()

        # === LỊCH SỬ GIAO DỊCH ===
        hist_label = ctk.CTkLabel(self, text="📋 Lịch sử giao dịch của xe đang kiểm tra", font=ctk.CTkFont(size=14, weight="bold"))
        hist_label.grid(row=4, column=0, columnspan=2, pady=(15,5), sticky="w", padx=20)

        self.history_scroll_ra = ctk.CTkScrollableFrame(self, height=140)
        self.history_scroll_ra.grid(row=5, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
