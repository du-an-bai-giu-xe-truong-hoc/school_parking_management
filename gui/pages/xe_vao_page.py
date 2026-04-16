# gui/pages/xe_vao_page.py
import customtkinter as ctk
from styles import AppStyle
from utils.api_client import ApiClient
from utils.helpers import Helper
from utils.hardware_controller import HardwareController

class XeVaoPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="#0F172A")
        self.main_app = main_app
        self.hardware = HardwareController()
        self.current_plate = None

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self, text="Xe Vào - Thông Tin Xe", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)

        # Làn A
        self.create_lane_frame("Làn A", 0, "A")
        # Làn B
        self.create_lane_frame("Làn B", 1, "B")

        # Nút quét cả hai làn
        btn_scan = ctk.CTkButton(self, text="🚗 Quét Xe Vào (Cả 2 làn)", font=ctk.CTkFont(size=16, weight="bold"),
                                 height=50, fg_color=AppStyle.ACCENT, command=self.scan_all_lanes)
        btn_scan.grid(row=2, column=0, columnspan=2, pady=15, padx=20, sticky="ew")

    def create_lane_frame(self, title: str, col: int, lane: str):
        frame = ctk.CTkFrame(self, fg_color="#1E2937")
        frame.grid(row=1, column=col, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)

        # Camera placeholder
        camera_lbl = ctk.CTkLabel(frame, text=f"📷 Camera Làn {lane}\n(Đang chờ xe...)", 
                                  width=320, height=180, fg_color="#334155", corner_radius=8)
        camera_lbl.pack(pady=8, padx=8)

        # Thông tin xe
        info_frame = ctk.CTkFrame(frame, fg_color="#0F172A")
        info_frame.pack(fill="x", padx=10, pady=5)

        self.plate_label = ctk.CTkLabel(info_frame, text="Biển số xe: ________", font=ctk.CTkFont(size=15))
        self.plate_label.pack(anchor="w", padx=10, pady=2)
        self.id_label = ctk.CTkLabel(info_frame, text="ID Thẻ SV: ________", font=ctk.CTkFont(size=15))
        self.id_label.pack(anchor="w", padx=10, pady=2)
        self.time_label = ctk.CTkLabel(info_frame, text="Thời gian vào: ________", font=ctk.CTkFont(size=15))
        self.time_label.pack(anchor="w", padx=10, pady=2)

        # Nút xác nhận mở barrier
        btn_confirm = ctk.CTkButton(frame, text="✅ Xác nhận & Mở Barrier", fg_color=AppStyle.SUCCESS,
                                    command=lambda: self.confirm_entry(lane))
        btn_confirm.pack(pady=10, padx=10, fill="x")

        # === LỊCH SỬ GIAO DỊCH CHI TIẾT ===
        hist_label = ctk.CTkLabel(frame, text="📋 Lịch sử giao dịch của xe", font=ctk.CTkFont(size=14, weight="bold"))
        hist_label.pack(anchor="w", padx=10, pady=(15,5))

        self.history_scroll = ctk.CTkScrollableFrame(frame, height=140)
        self.history_scroll.pack(fill="x", padx=10, pady=5)

        # Lưu reference
        setattr(self, f"lane_{lane}_plate_label", self.plate_label)
        setattr(self, f"lane_{lane}_history_scroll", self.history_scroll)

    def scan_all_lanes(self):
        Helper.show_toast(self, "Đang quét camera...", "#3B82F6")
        # Simulate + gọi API thực tế
        result_a = ApiClient.check_vehicle("29A-123.45", "A")
        result_b = ApiClient.check_vehicle("77A-364.24", "B")

        if "error" in result_a:
            Helper.show_toast(self, result_a["error"], AppStyle.DANGER)
            return

        # Update làn A
        self.lane_A_plate_label.configure(text=f"Biển số xe: {result_a.get('plate', '29A-123.45')}")
        self.load_vehicle_history(result_a.get('plate'))

        # Tương tự làn B...

    def load_vehicle_history(self, plate: str):
        """Tải lịch sử giao dịch chi tiết của xe"""
        self.current_plate = plate
        data = ApiClient.get_transaction_history(plate)
        if "error" in data:
            Helper.show_toast(self, data["error"], AppStyle.DANGER)
            return

        # Xóa lịch sử cũ
        for widget in self.lane_A_history_scroll.winfo_children():  # hoặc lane tương ứng
            widget.destroy()

        # Header bảng
        headers = ["Thời gian", "Hành động", "Số dư trước", "Số dư sau", "Người trực"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.lane_A_history_scroll, text=h, font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=i, padx=8, pady=4)

        # Dữ liệu
        for idx, log in enumerate(data.get("transactions", [])[:5], 1):
            ctk.CTkLabel(self.lane_A_history_scroll, text=log.get("timestamp", "")).grid(row=idx, column=0, padx=8, pady=3)
            ctk.CTkLabel(self.lane_A_history_scroll, text=log.get("action", "")).grid(row=idx, column=1, padx=8, pady=3)
            ctk.CTkLabel(self.lane_A_history_scroll, text=str(log.get("balance_before", ""))).grid(row=idx, column=2, padx=8, pady=3)
            ctk.CTkLabel(self.lane_A_history_scroll, text=str(log.get("balance_after", ""))).grid(row=idx, column=3, padx=8, pady=3)
            ctk.CTkLabel(self.lane_A_history_scroll, text=log.get("staff", "Bảo vệ")).grid(row=idx, column=4, padx=8, pady=3)

    def confirm_entry(self, lane: str):
        if not self.current_plate:
            Helper.show_toast(self, "Chưa có biển số xe!", AppStyle.DANGER)
            return
        result = ApiClient.check_vehicle(self.current_plate, lane)
        if result.get("status") == "approved" and result.get("balance_enough", False):
            self.hardware.open_barrier(lane)
            Helper.show_toast(self, f"✅ Xe vào làn {lane} - Barrier mở!", AppStyle.SUCCESS)
            self.load_vehicle_history(self.current_plate)   # refresh lịch sử
        else:
            Helper.show_toast(self, "❌ Xe không hợp lệ hoặc không đủ tiền!", AppStyle.DANGER)
