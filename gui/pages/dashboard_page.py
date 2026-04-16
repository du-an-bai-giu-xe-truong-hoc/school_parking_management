# gui/pages/dashboard_page.py
import customtkinter as ctk
from styles import AppStyle
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk

class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="transparent")
        self.main_app = main_app

        # Header dashboard
        top_frame = ctk.CTkFrame(self, fg_color=AppStyle.CARD_BG)
        top_frame.pack(fill="x", padx=15, pady=10)

        # Tổng sức chứa + progress circle
        ctk.CTkLabel(top_frame, text="Tổng Sức Chứa\n600 / 1000 Xe", font=("Helvetica", 22, "bold")).pack(side="left", padx=30)
        self.progress = ctk.CTkProgressBar(top_frame, width=180, height=180, mode="determinate")
        self.progress.set(0.6)
        self.progress.pack(side="left", padx=30)
        ctk.CTkLabel(top_frame, text="60%", font=("Helvetica", 48, "bold"), text_color=AppStyle.PRIMARY).pack(side="left")

        # 3 Card Khu A/B/C
        card_frame = ctk.CTkFrame(self, fg_color="transparent")
        card_frame.pack(fill="x", padx=15, pady=10)
        self._create_zone_card(card_frame, "Khu A (Đang chờ)", "150 / 250 Xe", 0)
        self._create_zone_card(card_frame, "Khu B (Tầng 1)", "200 / 350 Xe", 1)
        self._create_zone_card(card_frame, "Khu C (Tầng 2)", "250 / 400 Xe", 2)

        # Biểu đồ theo giờ
        self._create_hourly_chart()

        # Bảng lịch trực
        self._create_duty_table()

    def _create_zone_card(self, parent, title, count, col):
        card = ctk.CTkFrame(parent, fg_color=AppStyle.CARD_BG, corner_radius=12)
        card.grid(row=0, column=col, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=("Helvetica", 15, "bold")).pack(pady=8)
        ctk.CTkLabel(card, text=count, font=("Helvetica", 24, "bold"), text_color=AppStyle.PRIMARY).pack()

    def _create_hourly_chart(self):
        fig, ax = plt.subplots(figsize=(10, 3))
        hours = ["8h", "9h", "10h", "11h", "12h", "13h", "14h", "15h"]
        xe_vao = [8, 15, 22, 18, 12, 25, 10, 8]
        xe_ra = [5, 12, 18, 20, 15, 10, 6, 4]
        ax.bar(hours, xe_vao, color="#10B981", label="Xe Vào (Xanh)")
        ax.bar(hours, xe_ra, color="#EF4444", label="Xe Ra (Cam)", bottom=xe_vao)
        ax.set_title("THỐNG KÊ XE RA VÀO THEO GIỜ (15/11/2023)")
        canvas = FigureCanvasTkAgg(fig, self)
        canvas.get_tk_widget().pack(fill="x", padx=15, pady=10)

    def _create_duty_table(self):
        # Sử dụng CTkTable hoặc Treeview cho bảng lịch trực tuần này
        pass  # Bạn có thể bổ sung ttk.Treeview ở đây
