# gui/pages/dashboard_page.py
import customtkinter as ctk
from styles import AppStyle
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from utils.api_client import ApiClient
import pandas as pd
class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        # Sức chứa bãi xe
        header = ctk.CTkLabel(self, text="SỨC CHỨA BÃI XE", font=ctk.CTkFont(size=18, weight="bold"))
        header.pack(pady=10)
        # Pie chart (60%)
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.pie([60, 40], labels=["Đang đỗ", "Trống"], colors=[AppStyle.ACCENT, "#64748B"], autopct='%1.0f%%')
        canvas = FigureCanvasTkAgg(fig, self)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=10)
        # Khu A, B, C
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=20, pady=10)
        # (thêm label Khu A 150/250, Khu B 200/350, Khu C 250/400 theo ảnh)
        # Biểu đồ cột xe ra/vào theo giờ
        self.load_bar_chart()
        # Lịch trực bảo vệ
        self.load_schedule_table()
    def load_bar_chart(self):
        # Gọi API /stats/dashboard
        data = ApiClient.get_dashboard()
        if "error" in data:
            ctk.CTkLabel(self, text=data["error"], text_color=AppStyle.DANGER).pack()
            return
        # Vẽ bar chart với matplotlib (xe vào xanh, xe ra cam) theo ảnh
    def load_schedule_table(self):
        # Bảng lịch trực tuần này (Ca 1,2,3)
        pass # implement grid hoặc CTkTable với data từ API
