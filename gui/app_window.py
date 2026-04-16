# gui/app_window.py
import customtkinter as ctk
from styles import AppStyle
from pages.dashboard_page import DashboardPage
from pages.xe_vao_page import XeVaoPage
from pages.xe_ra_page import XeRaPage
from utils.api_client import ApiClient
import logging
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        AppStyle.apply_theme()
        self.title("App Quản Lý Xe - Bãi Giữ Xe Trường Học")
        self.geometry("1400x900")
        self.minsize(1200, 800)
        # Header giống ảnh
        self.header = ctk.CTkFrame(self, height=60, fg_color=AppStyle.PRIMARY)
        self.header.pack(fill="x")
        ctk.CTkLabel(self.header, text="App Quản Lý Xe", font=ctk.CTkFont(size=20, weight="bold"), text_color="white").pack(side="left", padx=20, pady=15)
        # Tabview
        self.tabview = ctk.CTkTabview(self, fg_color="#1E2937")
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabview.add("Xe Vào")
        self.tabview.add("Xe Ra")
        self.tabview.add("Thông Tin")
        # Gắn các page
        self.dashboard_page = DashboardPage(self.tabview.tab("Thông Tin"), self)
        self.xe_vao_page = XeVaoPage(self.tabview.tab("Xe Vào"), self)
        self.xe_ra_page = XeRaPage(self.tabview.tab("Xe Ra"), self)
        # Footer status
        self.status_bar = ctk.CTkLabel(self, text="✅ Backend connected | Barrier ready", text_color=AppStyle.SUCCESS, anchor="w")
        self.status_bar.pack(fill="x", padx=10, pady=5)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    def on_closing(self):
        logging.info("Đóng ứng dụng")
        self.destroy()
