# gui/pages/dashboard_page.py
import customtkinter as ctk
from styles import AppStyle
from utils.api_client import ApiClient
from utils.helpers import Helper
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="#0F172A")
        self.main_app = main_app

        # Header chính
        ctk.CTkLabel(self, text="THÔNG TIN TỔNG QUAN", 
                    font=ctk.CTkFont(size=24, weight="bold")).pack(pady=15)

        # === SỨC CHỨA BÃI XE ===
        capacity_frame = ctk.CTkFrame(self)
        capacity_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(capacity_frame, text="SỨC CHỨA BÃI XE", 
                    font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=4, pady=5)

        # Pie chart 60%
        self.create_pie_chart(capacity_frame)

        # Chi tiết Khu A, B, C
        self.create_capacity_details(capacity_frame)

        # === THỐNG KÊ XE RA VÀO THEO GIỜ ===
        self.create_hourly_chart()

        # === LỊCH TRỰC BẢO VỆ TUẦN NÀY (HOÀN THIỆN) ===
        self.create_schedule_table()

    def create_pie_chart(self, parent):
        fig, ax = plt.subplots(figsize=(3.5, 3.5))
        ax.pie([60, 40], labels=["Đang đỗ 600", "Trống 400"], 
               colors=[AppStyle.ACCENT, "#64748B"], autopct='%1.0f%%', startangle=90)
        ax.set_title("Tổng sức chứa\n600 / 1000 Xe", fontsize=12)
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, padx=20, pady=10)

    def create_capacity_details(self, parent):
        details = [
            ("Khu A (Đuôi 1)", "150 / 250 Xe"),
            ("Khu B (Tầng 1)", "200 / 350 Xe"),
            ("Khu C (Tầng 2)", "250 / 400 Xe")
        ]
        for i, (name, value) in enumerate(details):
            frame = ctk.CTkFrame(parent, fg_color="#1E2937")
            frame.grid(row=1, column=i+1, padx=8, pady=10, sticky="nsew")
            ctk.CTkLabel(frame, text=name, font=ctk.CTkFont(size=13)).pack(pady=5)
            ctk.CTkLabel(frame, text=value, text_color=AppStyle.ACCENT, 
                        font=ctk.CTkFont(size=16, weight="bold")).pack()

    def create_hourly_chart(self):
        chart_frame = ctk.CTkFrame(self)
        chart_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(chart_frame, text="THỐNG KÊ XE RA VÀO THEO GIỜ (15/11/2023)", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)

        data = ApiClient.get_dashboard()
        if "error" in data:
            Helper.show_toast(self, data["error"], "#EF4444")
            return

        fig, ax = plt.subplots(figsize=(12, 4))
        hours = ["8h", "9h", "10h", "11h", "12h", "13h", "14h", "15h"]
        xe_vao = [120, 180, 250, 300, 280, 220, 150, 90]
        xe_ra = [80, 140, 200, 260, 240, 190, 130, 70]

        ax.bar(hours, xe_vao, color=AppStyle.ACCENT, label="Xe Vào")
        ax.bar(hours, xe_ra, color="#F59E0B", label="Xe Ra", alpha=0.8)
        ax.set_ylabel("Số lượng xe")
        ax.legend()
        canvas = FigureCanvasTkAgg(fig, chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=10)

    def create_schedule_table(self):
        """Bảng Lịch trực bảo vệ tuần này - Khớp 100% ảnh"""
        table_frame = ctk.CTkFrame(self, fg_color="#1E2937")
        table_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(table_frame, text="LỊCH TRỰC BẢO VỆ TUẦN NÀY (Tuần 46: 13/11 - 19/11)", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))

        # Header
        headers = ["Thứ / Ngày", "Ca 1 (7h-15h)", "Ca 2 (15h-23h)", "Ca 3 (23h-7h)"]
        header_frame = ctk.CTkFrame(table_frame, fg_color="#0F172A")
        header_frame.pack(fill="x", padx=5, pady=5)

        for col, text in enumerate(headers):
            lbl = ctk.CTkLabel(header_frame, text=text, font=ctk.CTkFont(size=14, weight="bold"),
                              text_color=AppStyle.TEXT_LIGHT)
            lbl.grid(row=0, column=col, padx=12, pady=8, sticky="nsew")
            header_frame.grid_columnconfigure(col, weight=1)

        # Dữ liệu lịch trực (theo ảnh bạn cung cấp)
        schedule_data = [
            ["Thứ 2 (14/11)", "Nguyễn Văn A", "Trần Thị B", "Lê Văn C"],
            ["Thứ 3 (15/11)", "Nguyễn Văn B", "Lê Thị C", "Trần Văn A"],
            ["Thứ 4 (16/11)", "Trần Thị B", "Nguyễn Văn A", "Lê Văn C"],
            ["Thứ 5 (17/11)", "Lê Thị C", "Trần Văn A", "Nguyễn Văn B"],
            ["Thứ 6 (18/11)", "Nguyễn Văn A", "Lê Văn C", "Trần Thị B"],
            ["Thứ 7 (19/11)", "Trần Văn A", "Nguyễn Văn B", "Lê Thị C"],
            ["Chủ Nhật (20/11)", "Lê Văn C", "Trần Thị B", "Nguyễn Văn A"],
        ]

        # Tạo các dòng dữ liệu
        data_frame = ctk.CTkFrame(table_frame, fg_color="#1E2937")
        data_frame.pack(fill="x", padx=5, pady=5)

        for row_idx, row_data in enumerate(schedule_data):
            for col_idx, cell_text in enumerate(row_data):
                color = AppStyle.TEXT_LIGHT if col_idx == 0 else "#E2E8F0"
                lbl = ctk.CTkLabel(data_frame, text=cell_text, 
                                  font=ctk.CTkFont(size=13),
                                  text_color=color)
                lbl.grid(row=row_idx, column=col_idx, padx=12, pady=6, sticky="nsew")
                data_frame.grid_columnconfigure(col_idx, weight=1)

        # === KẾT NỐI API (sẵn sàng mở rộng) ===
        # data = ApiClient.get("/schedule/week")
        # if "error" not in data:
        #     schedule_data = data["schedule"]  # format giống list trên

        Helper.log_info("Đã load bảng lịch trực bảo vệ thành công")
