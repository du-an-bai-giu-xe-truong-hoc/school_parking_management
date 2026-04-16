# gui/pages/xe_vao_page.py
import customtkinter as ctk
from styles import AppStyle
from utils.api_client import ApiClient
from utils.hardware_controller import HardwareController

class XeVaoPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.hardware = HardwareController()

        # Hai làn camera
        frame_lanes = ctk.CTkFrame(self)
        frame_lanes.pack(fill="x", padx=20, pady=10)
        for lane in ["Làn A (Vào)", "Làn B (Vào)"]:
            ctk.CTkLabel(frame_lanes, text=lane, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=40)

        # Nút quét xe
        btn_scan = ctk.CTkButton(self, text="📸 QUÉT XE VÀO", 
                                 font=ctk.CTkFont(size=18), height=50,
                                 fg_color=AppStyle.SUCCESS,
                                 command=self.scan_xe_vao)
        btn_scan.pack(pady=20, padx=30, fill="x")

        self.result_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=16))
        self.result_label.pack(pady=10)

    def scan_xe_vao(self):
        # Simulate hoặc dùng pyzbar sau
        plate = "51F-123.45"  # test
        data = ApiClient.check_vehicle(plate, lane="A")
        if "error" in data:
            self.result_label.configure(text=data["error"], text_color=AppStyle.DANGER)
            return

        if data.get("status") == "approved":
            self.result_label.configure(text=f"✅ Xe {plate} được phép vào\nSố dư: {data.get('balance')}đ", 
                                       text_color=AppStyle.SUCCESS)
            self.hardware.open_barrier("A")
        else:
            self.result_label.configure(text="❌ Không cho qua\n" + data.get("reason", ""), 
                                       text_color=AppStyle.DANGER)
