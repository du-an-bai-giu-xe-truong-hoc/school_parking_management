# gui/pages/xe_ra_page.py
import customtkinter as ctk
from styles import AppStyle
from utils.api_client import ApiClient
from utils.hardware_controller import HardwareController

class XeRaPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.hardware = HardwareController()

        ctk.CTkLabel(self, text="🚪 XE RA", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=10)

        btn_scan_ra = ctk.CTkButton(self, text="📸 QUÉT XE RA", 
                                    font=ctk.CTkFont(size=18), height=50,
                                    fg_color=AppStyle.ACCENT,
                                    command=self.scan_xe_ra)
        btn_scan_ra.pack(pady=20, padx=30, fill="x")

        self.result_ra = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=16))
        self.result_ra.pack(pady=10)

    def scan_xe_ra(self):
        plate = "51F-123.45"  # test
        data = ApiClient.check_vehicle(plate, lane="A")
        if "error" in data:
            self.result_ra.configure(text=data["error"], text_color=AppStyle.DANGER)
            return

        if data.get("status") == "approved":
            self.result_ra.configure(text=f"✅ Xe {plate} ra thành công\nSố dư còn: {data.get('balance')}đ", 
                                    text_color=AppStyle.SUCCESS)
            self.hardware.open_barrier("A")
        else:
            self.result_ra.configure(text="❌ Không cho ra\n" + data.get("reason", ""), 
                                    text_color=AppStyle.DANGER)
