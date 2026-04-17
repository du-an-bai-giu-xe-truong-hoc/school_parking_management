from datetime import datetime
import os
from tkinter import messagebox

import customtkinter as ctk

if (__package__ or "").startswith("gui"):
    from ..styles import AppStyle
    from ..utils.api_client import ApiClient
    from ..utils.camera import CameraHandler, IoTCameraHandler
    from ..utils.hardware_controller import HardwareController
else:
    from styles import AppStyle
    from utils.api_client import ApiClient
    from utils.camera import CameraHandler, IoTCameraHandler
    from utils.hardware_controller import HardwareController

class XeVaoPage(ctk.CTkFrame):
    def __init__(self, parent, main_app, on_transaction_updated=None):
        super().__init__(parent, fg_color="transparent")
        self.main_app = main_app
        self.on_transaction_updated = on_transaction_updated
        self.hardware = HardwareController()
        self.hardware.connect()

        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(0, weight=1)

        self._build_camera_panel()
        self._build_form_panel()

    def _build_camera_panel(self):
        panel = ctk.CTkFrame(self, fg_color=AppStyle.CARD_BG, corner_radius=12)
        panel.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")

        ctk.CTkLabel(
            panel,
            text="Camera laptop + camera IoT",
            text_color=AppStyle.PRIMARY,
            font=AppStyle.SUBTITLE_FONT,
        ).pack(anchor="w", padx=14, pady=(14, 8))

        ctk.CTkLabel(panel, text="Laptop camera (barcode + local image)", font=AppStyle.BODY_FONT).pack(
            anchor="w", padx=14, pady=(0, 4)
        )

        self.local_camera_label = ctk.CTkLabel(
            panel,
            text="Dang cho camera...",
            fg_color="#E2E8F0",
            width=640,
            height=240,
            corner_radius=10,
        )
        self.local_camera_label.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(panel, text="IoT ESP32 camera (http://192.168.81.61/capture)", font=AppStyle.BODY_FONT).pack(
            anchor="w", padx=14, pady=(0, 4)
        )

        self.iot_camera_label = ctk.CTkLabel(
            panel,
            text="Dang ket noi camera IoT...",
            fg_color="#E2E8F0",
            width=640,
            height=240,
            corner_radius=10,
        )
        self.iot_camera_label.pack(fill="x", padx=14, pady=(0, 10))

        self.camera_status_label = ctk.CTkLabel(
            panel,
            text="Barcode tu camera se tu dong dien vao form.",
            font=AppStyle.BODY_FONT,
            text_color="#334155",
        )
        self.camera_status_label.pack(anchor="w", padx=14, pady=(0, 10))

        camera_id = int(os.getenv("LAPTOP_CAMERA_ID", "0"))
        self.local_camera = CameraHandler(self.local_camera_label, callback=self._on_camera_barcode)
        self.local_camera.start(camera_id=camera_id)

        self.iot_camera = IoTCameraHandler(self.iot_camera_label)
        self.iot_camera.start()

    def _build_form_panel(self):
        panel = ctk.CTkFrame(self, fg_color=AppStyle.CARD_BG, corner_radius=12)
        panel.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

        ctk.CTkLabel(
            panel,
            text="Xu ly xe vao",
            text_color=AppStyle.PRIMARY,
            font=AppStyle.SUBTITLE_FONT,
        ).pack(anchor="w", padx=14, pady=(14, 10))

        self.entry_barcode = ctk.CTkEntry(panel, placeholder_text="Nhap/quet barcode")
        self.entry_barcode.pack(fill="x", padx=14, pady=6)

        self.entry_plate = ctk.CTkEntry(panel, placeholder_text="Bien so (co the de trong, he thong tu OCR)")
        self.entry_plate.pack(fill="x", padx=14, pady=6)

        option_frame = ctk.CTkFrame(panel, fg_color="transparent")
        option_frame.pack(fill="x", padx=14, pady=(6, 10))
        ctk.CTkLabel(option_frame, text="Lane", font=AppStyle.BODY_FONT).pack(side="left")
        self.lane_option = ctk.CTkOptionMenu(option_frame, values=["A", "B", "C"])
        self.lane_option.pack(side="left", padx=8)
        self.lane_option.set("A")

        button_row = ctk.CTkFrame(panel, fg_color="transparent")
        button_row.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkButton(
            button_row,
            text="Tra cuu DB",
            fg_color="#0EA5E9",
            command=self._preview_vehicle,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            button_row,
            text="Xac nhan xe vao",
            fg_color=AppStyle.SUCCESS,
            command=self._submit_entry,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            button_row,
            text="Xoa form",
            fg_color="#64748B",
            command=self._clear_form,
        ).pack(side="left")

        info_frame = ctk.CTkFrame(panel, fg_color="#F8FAFC")
        info_frame.pack(fill="x", padx=14, pady=(0, 10))

        self.lbl_owner = ctk.CTkLabel(info_frame, text="Chu xe: -", font=AppStyle.BODY_FONT)
        self.lbl_owner.pack(anchor="w", padx=10, pady=(8, 2))
        self.lbl_identity = ctk.CTkLabel(info_frame, text="Ma dinh danh: -", font=AppStyle.BODY_FONT)
        self.lbl_identity.pack(anchor="w", padx=10, pady=2)
        self.lbl_balance = ctk.CTkLabel(info_frame, text="So du: -", font=AppStyle.BODY_FONT)
        self.lbl_balance.pack(anchor="w", padx=10, pady=2)
        self.lbl_lock = ctk.CTkLabel(info_frame, text="Khoa xe: -", font=AppStyle.BODY_FONT)
        self.lbl_lock.pack(anchor="w", padx=10, pady=(2, 8))

        ctk.CTkLabel(panel, text="Ket qua doi soat", font=("Helvetica", 16, "bold")).pack(
            anchor="w",
            padx=14,
            pady=(4, 8),
        )

        self.result_box = ctk.CTkTextbox(panel, height=260)
        self.result_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.result_box.insert("1.0", "Chua co giao dich xe vao.")
        self.result_box.configure(state="disabled")

    def _on_camera_barcode(self, code: str):
        self.after(0, lambda: self._set_barcode_from_camera(code))

    def _set_barcode_from_camera(self, code: str):
        value = (code or "").strip()
        if not value:
            return
        self.entry_barcode.delete(0, "end")
        self.entry_barcode.insert(0, value)
        self.camera_status_label.configure(text=f"Da quet barcode: {value}")
        self._preview_vehicle()

    def _preview_vehicle(self):
        qr_code = self.entry_barcode.get().strip()
        if not qr_code:
            return

        preview = ApiClient.preview_vehicle(qr_code=qr_code, bien_so=self.entry_plate.get().strip())
        if preview is None:
            return

        self._render_preview(preview)

    def _render_preview(self, data: dict):
        self.lbl_owner.configure(text=f"Chu xe: {data.get('owner_name', '-')}")
        self.lbl_identity.configure(text=f"Ma dinh danh: {data.get('owner_identity_card', '-')}")
        self.lbl_balance.configure(text=f"So du: {data.get('owner_balance', '-')}")
        locked = bool(data.get("vehicle_locked"))
        reason = data.get("lock_reason") or "-"
        self.lbl_lock.configure(text=f"Khoa xe: {'CO' if locked else 'KHONG'} | Ly do: {reason}")

    def _submit_entry(self):
        qr_code = self.entry_barcode.get().strip()
        plate = self.entry_plate.get().strip()
        lane = self.lane_option.get().strip()

        if not qr_code:
            messagebox.showwarning("Thieu du lieu", "Can co barcode de xu ly xe vao.")
            return

        local_image_base64 = self.local_camera.get_latest_frame_base64()
        if not local_image_base64:
            messagebox.showwarning("Loi camera", "Khong lay duoc anh tu camera laptop. Vui long kiem tra camera.")
            return

        result = ApiClient.process_entry(
            qr_code=qr_code,
            bien_so=plate,
            lane=lane,
            local_image_base64=local_image_base64,
        )
        if result is None:
            messagebox.showerror("Loi API", "Khong the ket noi backend de xu ly xe vao.")
            return

        self._render_preview(result)
        self._render_result(result)

        if result.get("status") == "success" and result.get("decision") == "allow":
            self.hardware.open_barrier(lane=lane)
            messagebox.showinfo("Xe vao", "Xe vao hop le. Barrier da mo.")
            if callable(self.on_transaction_updated):
                self.on_transaction_updated()
        else:
            messagebox.showwarning("Can xac minh", result.get("message", "Can kiem tra thu cong."))

    def _render_result(self, data: dict):
        time_in = self._format_time(data.get("time_in"))
        lines = [
            f"Trang thai: {data.get('status', '-')}",
            f"Hanh dong: {data.get('action', '-')}",
            f"Quyet dinh: {data.get('decision', '-')}",
            f"Ti le khop: {data.get('similarity_score', 0)}% (nguong {data.get('threshold', 0)}%)",
            f"Khop chuoi: {data.get('string_similarity_score', '-')}",
            f"Bien so quet: {data.get('scanned_plate', '-')}",
            f"Bien so DB: {data.get('db_license_plate', '-')}",
            f"Chu xe: {data.get('owner_name', '-')}",
            f"So du: {data.get('owner_balance', '-')}",
            f"Ma giao dich: {data.get('transaction_id', '-')}",
            f"Thoi gian vao: {time_in}",
            f"Mo cong (giay): {data.get('gate_open_seconds', 0)}",
            f"Anh IoT vao: {data.get('entry_iot_image_path', '-')}",
            f"Anh local vao: {data.get('entry_local_image_path', '-')}",
            f"Thong diep: {data.get('message', '-')}",
        ]
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", "\n".join(lines))
        self.result_box.configure(state="disabled")

    def _format_time(self, value):
        if not value:
            return "-"
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed.strftime("%H:%M:%S %d/%m/%Y")
            except ValueError:
                return value
        if isinstance(value, datetime):
            return value.strftime("%H:%M:%S %d/%m/%Y")
        return str(value)

    def _clear_form(self):
        self.entry_barcode.delete(0, "end")
        self.entry_plate.delete(0, "end")
        self.lbl_owner.configure(text="Chu xe: -")
        self.lbl_identity.configure(text="Ma dinh danh: -")
        self.lbl_balance.configure(text="So du: -")
        self.lbl_lock.configure(text="Khoa xe: -")
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", "Chua co giao dich xe vao.")
        self.result_box.configure(state="disabled")
