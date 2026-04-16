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
        self.grid_rowconfigure(6, weight=1)

        # === CẢNH BÁO KHÓA XE (đỏ) ===
        self.warning_frame = ctk.CTkFrame(self, fg_color=AppStyle.DANGER, height=50)
        self.warning_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.warning_label = ctk.CTkLabel(
            self.warning_frame,
            text="🚨 CẢNH BÁO KHÓA XE - Biển số: ________",
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.warning_label.pack(pady=12)

        # Title
        ctk.CTkLabel(self, text="Xe Ra - So sánh & Xử lý", 
                     font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=1, column=0, columnspan=2, pady=8)

        # Camera so sánh
        self.create_camera_comparison()

        # Bảng so sánh thông tin
        self.create_comparison_table()

        # Nút hành động
        self.create_action_buttons()

        # === LỊCH SỬ GIAO DỊCH CHI TIẾT ===
        hist_label = ctk.CTkLabel(self, text="📋 Lịch sử giao dịch của xe đang kiểm tra",
                                  font=ctk.CTkFont(size=14, weight="bold"))
        hist_label.grid(row=4, column=0, columnspan=2, pady=(20, 5), sticky="w", padx=25)

        self.history_scroll = ctk.CTkScrollableFrame(self, height=160)
        self.history_scroll.grid(row=5, column=0, columnspan=2, padx=25, pady=5, sticky="ew")

        # Nút refresh lịch sử
        ctk.CTkButton(self, text="🔄 Refresh Lịch sử", 
                      command=self.refresh_history).grid(
            row=6, column=0, columnspan=2, pady=10)

    def create_camera_comparison(self):
        frame = ctk.CTkFrame(self, fg_color="#1E2937")
        frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        # Camera lúc vào
        left = ctk.CTkFrame(frame, fg_color="#334155")
        left.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        ctk.CTkLabel(left, text="Ảnh Camera Lúc Vào", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        self.img_vao = ctk.CTkLabel(left, text="📸 29A-123.45\n10:15 15/11/2023", 
                                    width=300, height=160, fg_color="#475569")
        self.img_vao.pack(pady=8)

        # Camera lúc ra
        right = ctk.CTkFrame(frame, fg_color="#334155")
        right.pack(side="right", expand=True, fill="both", padx=10, pady=10)
        ctk.CTkLabel(right, text="Ảnh Camera Lúc Ra", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        self.img_ra = ctk.CTkLabel(right, text="📸 77A-364.24\n11:30 15/11/2023", 
                                   width=300, height=160, fg_color="#475569")
        self.img_ra.pack(pady=8)

    def create_comparison_table(self):
        table = ctk.CTkFrame(self, fg_color="#1E2937")
        table.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        headers = ["Thông tin", "Xe vào", "Xe ra"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(table, text=h, font=ctk.CTkFont(size=14, weight="bold")).grid(
                row=0, column=i, padx=15, pady=8)

        data = [
            ("Biển số xe", "29A-123.45", "77A-364.24"),
            ("ID Thẻ SV", "SV211234", "SV77078"),
            ("Vị trí đậu", "Khu C", "Khu B"),
            ("Thời gian", "10:15", "11:30")
        ]
        for r, row in enumerate(data, 1):
            for c, val in enumerate(row):
                ctk.CTkLabel(table, text=val, font=ctk.CTkFont(size=13)).grid(
                    row=r, column=c, padx=15, pady=6, sticky="w")

    def create_action_buttons(self):
        btn_frame = ctk.CTkFrame(self, fg_color="#1E2937")
        btn_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        ctk.CTkButton(btn_frame, text="✅ Có phải xe chính chủ?", 
                      fg_color=AppStyle.SUCCESS, height=45,
                      command=self.confirm_owner).pack(side="left", expand=True, padx=8)

        ctk.CTkButton(btn_frame, text="❌ Không phải xe chính chủ", 
                      fg_color=AppStyle.DANGER, height=45,
                      command=self.reject_vehicle).pack(side="left", expand=True, padx=8)

        ctk.CTkButton(btn_frame, text="🚧 Mở Barrier", 
                      fg_color=AppStyle.ACCENT, height=45,
                      command=self.open_barrier_ra).pack(side="left", expand=True, padx=8)

        ctk.CTkButton(btn_frame, text="📄 In biên bản", 
                      fg_color="#64748B", height=45,
                      command=lambda: Helper.show_toast(self, "Đã in biên bản thành công!", AppStyle.SUCCESS)).pack(
            side="left", expand=True, padx=8)

    def load_vehicle_history(self, plate: str):
        """Tải lịch sử giao dịch chi tiết của xe"""
        self.current_plate = plate
        data = ApiClient.get_transaction_history(plate=plate)

        if "error" in data:
            Helper.show_toast(self, data["error"], AppStyle.DANGER)
            return

        # Xóa lịch sử cũ
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        # Header bảng
        headers = ["Thời gian", "Hành động", "Số dư trước", "Số dư sau", "Người trực"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.history_scroll, text=h, 
                        font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=0, column=i, padx=10, pady=6)

        # Dữ liệu
        for idx, log in enumerate(data.get("transactions", [])[:6], 1):
            ctk.CTkLabel(self.history_scroll, text=log.get("timestamp", "—")).grid(
                row=idx, column=0, padx=10, pady=4)
            ctk.CTkLabel(self.history_scroll, text=log.get("action", "—")).grid(
                row=idx, column=1, padx=10, pady=4)
            ctk.CTkLabel(self.history_scroll, text=str(log.get("balance_before", "—"))).grid(
                row=idx, column=2, padx=10, pady=4)
            ctk.CTkLabel(self.history_scroll, text=str(log.get("balance_after", "—"))).grid(
                row=idx, column=3, padx=10, pady=4)
            ctk.CTkLabel(self.history_scroll, text=log.get("staff", "Bảo vệ")).grid(
                row=idx, column=4, padx=10, pady=4)

    def refresh_history(self):
        if self.current_plate:
            self.load_vehicle_history(self.current_plate)
        else:
            Helper.show_toast(self, "Chưa có xe đang kiểm tra!", AppStyle.WARNING)

    def confirm_owner(self):
        if not self.current_plate:
            Helper.show_toast(self, "Chưa có biển số xe!", AppStyle.DANGER)
            return
        Helper.show_toast(self, "Đang kiểm tra số dư...", "#3B82F6")
        result = ApiClient.post("/transactions/confirm_exit", {"plate": self.current_plate})
        if result.get("status") == "approved":
            self.hardware.open_barrier("B")
            Helper.show_toast(self, "✅ Xe ra thành công - Barrier đã mở!", AppStyle.SUCCESS)
            self.load_vehicle_history(self.current_plate)   # refresh lịch sử
        else:
            Helper.show_toast(self, "❌ Không đủ điều kiện mở barrier!", AppStyle.DANGER)

    def reject_vehicle(self):
        Helper.show_toast(self, "❌ Đã từ chối xe ra - Gửi cảnh báo quản lý!", AppStyle.DANGER)
        # Có thể gọi API gửi thông báo ở đây

    def open_barrier_ra(self):
        """Mở barrier thủ công (chỉ dùng khi đã xác nhận)"""
        if not self.current_plate:
            Helper.show_toast(self, "Chưa có xe!", AppStyle.DANGER)
            return
        self.hardware.open_barrier("B")
        Helper.show_toast(self, "🚧 Barrier mở làn Ra!", AppStyle.SUCCESS)
        self.load_vehicle_history(self.current_plate)
