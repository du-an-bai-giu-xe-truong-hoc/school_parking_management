# gui/app_window.py
import customtkinter as ctk
from datetime import datetime

# SỬA IMPORT Ở ĐÂY (bỏ dấu chấm)
from styles import AppStyle
from pages.dashboard_page import DashboardPage
from pages.xe_vao_page import XeVaoPage
from pages.xe_ra_page import XeRaPage
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        AppStyle.apply()
        self.title("App Quản Lý Xe")
        self.geometry("1400x900")
        self.minsize(1200, 700)

        # Header
        self.header = ctk.CTkFrame(self, height=60, fg_color=AppStyle.PRIMARY)
        self.header.pack(fill="x", padx=0, pady=0)
        self.header.pack_propagate(False)

        ctk.CTkLabel(self.header, text="P", font=("Helvetica", 28, "bold"),
                     text_color="white").pack(side="left", padx=15)
        ctk.CTkLabel(self.header, text="App Quản Lý Xe", font=("Helvetica", 22, "bold"),
                     text_color="white").pack(side="left", padx=5)

        self.time_label = ctk.CTkLabel(self.header, text="", font=("Helvetica", 14), text_color="white")
        self.time_label.pack(side="right", padx=20)
        self._update_time()

        ctk.CTkLabel(self.header, text="Nguyễn Văn A", font=("Helvetica", 14), text_color="white").pack(side="right", padx=10)

        ctk.CTkButton(self.header, text="🚨 Báo Động", fg_color=AppStyle.DANGER, width=120,
                      command=self.show_alert).pack(side="right", padx=8)
        ctk.CTkButton(self.header, text="📧 Góp ý", width=100).pack(side="right", padx=8)

        # Tabview
        self.tabview = ctk.CTkTabview(self, fg_color="transparent")
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tabview.add("Xe Vào")
        self.tabview.add("Xe Ra")
        self.tabview.add("Thông Tin")

        # Gắn page
        XeVaoPage(self.tabview.tab("Xe Vào"), self).pack(fill="both", expand=True)
        XeRaPage(self.tabview.tab("Xe Ra"), self).pack(fill="both", expand=True)
        DashboardPage(self.tabview.tab("Thông Tin"), self).pack(fill="both", expand=True)

    def _update_time(self):
        self.time_label.configure(text=datetime.now().strftime("%H:%M | %d/%m/%Y"))
        self.after(1000, self._update_time)

    def show_alert(self):
        ctk.CTkMessagebox(title="Báo Động", message="Đã gửi tín hiệu báo động!", icon="warning")
