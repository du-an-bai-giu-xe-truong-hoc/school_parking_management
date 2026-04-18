from datetime import datetime
import os
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

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

class XeRaPage(ctk.CTkFrame):
    def __init__(self, parent, main_app, on_transaction_updated=None):
        super().__init__(parent, fg_color="transparent")
        self.main_app = main_app
        self.on_transaction_updated = on_transaction_updated
        self.hardware = HardwareController()
        self.hardware.connect()
        self._waiting_capture = False
        self._camera_running = False

        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        panel = ctk.CTkFrame(self, fg_color=AppStyle.CARD_BG, corner_radius=12)
        panel.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")

        ctk.CTkLabel(
            panel,
            text="Xu ly xe ra",
            text_color=AppStyle.PRIMARY,
            font=AppStyle.SUBTITLE_FONT,
        ).pack(anchor="w", padx=14, pady=(14, 10))

        ctk.CTkLabel(panel, text="Laptop camera", font=AppStyle.BODY_FONT).pack(anchor="w", padx=14, pady=(0, 4))
        self.local_camera_label = ctk.CTkLabel(
            panel,
            text="Dang cho camera laptop...",
            fg_color="#E2E8F0",
            width=620,
            height=210,
            corner_radius=10,
        )
        self.local_camera_label.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(panel, text="IoT camera ESP32", font=AppStyle.BODY_FONT).pack(anchor="w", padx=14, pady=(0, 4))
        self.iot_camera_label = ctk.CTkLabel(
            panel,
            text="Dang ket noi camera IoT...",
            fg_color="#E2E8F0",
            width=620,
            height=210,
            corner_radius=10,
        )
        self.iot_camera_label.pack(fill="x", padx=14, pady=(0, 10))

        self.exit_local_camera = CameraHandler(
            self.local_camera_label,
            callback=self._on_exit_barcode,
            on_detection=self._on_exit_detection,
        )
        self.exit_iot_camera = IoTCameraHandler(
            self.iot_camera_label,
            on_detection=self._on_exit_detection,
        )

        self.exit_barcode = ctk.CTkEntry(panel, placeholder_text="Nhap/quet barcode")
        self.exit_barcode.pack(fill="x", padx=14, pady=6)

        self.exit_plate = ctk.CTkEntry(panel, placeholder_text="Bien so quet tu YOLOv8")
        self.exit_plate.pack(fill="x", padx=14, pady=6)

        self.capture_status = ctk.CTkLabel(
            panel,
            text="Dang quet bien so + REFC/QR bang khung do theo doi.",
            font=AppStyle.BODY_FONT,
            text_color="#334155",
        )
        self.capture_status.pack(anchor="w", padx=14, pady=(0, 8))

        option_frame = ctk.CTkFrame(panel, fg_color="transparent")
        option_frame.pack(fill="x", padx=14, pady=(6, 10))
        ctk.CTkLabel(option_frame, text="Lane", font=AppStyle.BODY_FONT).pack(side="left")
        self.exit_lane = ctk.CTkOptionMenu(option_frame, values=["A", "B", "C"])
        self.exit_lane.pack(side="left", padx=8)
        self.exit_lane.set("A")

        button_row = ctk.CTkFrame(panel, fg_color="transparent")
        button_row.pack(fill="x", padx=14, pady=(0, 10))

        self.btn_confirm_exit = ctk.CTkButton(
            button_row,
            text="Xac nhan xe ra (dung yen 2-3s)",
            fg_color=AppStyle.SUCCESS,
            command=self._submit_exit,
        )
        self.btn_confirm_exit.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            button_row,
            text="Xoa form",
            fg_color="#64748B",
            command=self._clear_form,
        ).pack(side="left")

        warning = ctk.CTkLabel(
            panel,
            text="Neu ti le khop duoi nguong he thong se yeu cau xac minh thu cong.",
            text_color="#9A3412",
            font=AppStyle.BODY_FONT,
            wraplength=460,
            justify="left",
        )
        warning.pack(fill="x", padx=14, pady=(4, 10))

        self.result_box = ctk.CTkTextbox(panel, height=280)
        self.result_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.result_box.insert("1.0", "Chua co giao dich xe ra.")
        self.result_box.configure(state="disabled")

    def _build_right_panel(self):
        panel = ctk.CTkFrame(self, fg_color=AppStyle.CARD_BG, corner_radius=12)
        panel.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

        ctk.CTkLabel(
            panel,
            text="Thong tin doi soat",
            text_color=AppStyle.PRIMARY,
            font=AppStyle.SUBTITLE_FONT,
        ).pack(anchor="w", padx=14, pady=(14, 10))

        self.lbl_score = ctk.CTkLabel(panel, text="Ty le khop: -", font=("Helvetica", 18, "bold"))
        self.lbl_score.pack(anchor="w", padx=14, pady=4)

        self.lbl_time_in = ctk.CTkLabel(panel, text="Thoi gian vao: -", font=AppStyle.BODY_FONT)
        self.lbl_time_in.pack(anchor="w", padx=14, pady=4)

        self.lbl_time_out = ctk.CTkLabel(panel, text="Thoi gian ra: -", font=AppStyle.BODY_FONT)
        self.lbl_time_out.pack(anchor="w", padx=14, pady=4)

        self.lbl_duration = ctk.CTkLabel(panel, text="Thoi gian gui: -", font=AppStyle.BODY_FONT)
        self.lbl_duration.pack(anchor="w", padx=14, pady=4)

        self.lbl_fee = ctk.CTkLabel(panel, text="Phi gui xe: -", font=("Helvetica", 16, "bold"))
        self.lbl_fee.pack(anchor="w", padx=14, pady=(6, 10))

        self.lbl_owner = ctk.CTkLabel(panel, text="Chu xe: -", font=AppStyle.BODY_FONT)
        self.lbl_owner.pack(anchor="w", padx=14, pady=4)

        self.lbl_balance = ctk.CTkLabel(panel, text="So du: -", font=AppStyle.BODY_FONT)
        self.lbl_balance.pack(anchor="w", padx=14, pady=4)

        self.lbl_lock = ctk.CTkLabel(panel, text="Khoa xe: -", font=AppStyle.BODY_FONT)
        self.lbl_lock.pack(anchor="w", padx=14, pady=4)

        self.lbl_decision = ctk.CTkLabel(panel, text="Quyet dinh: -", font=AppStyle.BODY_FONT)
        self.lbl_decision.pack(anchor="w", padx=14, pady=4)

        self.lbl_message = ctk.CTkLabel(
            panel,
            text="Thong diep: -",
            font=AppStyle.BODY_FONT,
            wraplength=470,
            justify="left",
        )
        self.lbl_message.pack(anchor="w", padx=14, pady=4)

        image_panel = ctk.CTkFrame(panel, fg_color="#F8FAFC")
        image_panel.pack(fill="both", expand=True, padx=14, pady=(8, 12))

        ctk.CTkLabel(image_panel, text="Anh vao (DB)", font=AppStyle.BODY_FONT).pack(anchor="w", padx=10, pady=(8, 4))
        self.entry_image_label = ctk.CTkLabel(
            image_panel,
            text="Chua co anh vao",
            fg_color="#E2E8F0",
            width=460,
            height=160,
            corner_radius=8,
        )
        self.entry_image_label.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(image_panel, text="Anh ra hien tai", font=AppStyle.BODY_FONT).pack(anchor="w", padx=10, pady=(0, 4))
        self.exit_image_label = ctk.CTkLabel(
            image_panel,
            text="Chua co anh ra",
            fg_color="#E2E8F0",
            width=460,
            height=160,
            corner_radius=8,
        )
        self.exit_image_label.pack(fill="x", padx=10, pady=(0, 10))

    def _on_exit_barcode(self, code: str):
        value = (code or "").strip()
        if not value:
            return
        self.after(0, lambda: self._set_exit_barcode(value))

    def _on_exit_detection(self, payload: dict):
        self.after(0, lambda p=payload: self._apply_exit_detection(p))

    def _apply_exit_detection(self, payload: dict):
        detection_type = str(payload.get("type", "")).strip().lower()
        value = str(payload.get("value", "")).strip()
        confidence = float(payload.get("confidence", 0.0) or 0.0)
        source = str(payload.get("source", "-")).strip()

        if not value:
            return

        self.capture_status.configure(
            text=f"[{source}] {detection_type.upper()}: {value} ({confidence:.1f}%)"
        )

        if detection_type == "plate" and confidence >= 45.0:
            current_plate = self.exit_plate.get().strip().upper()
            if current_plate != value.upper():
                self.exit_plate.delete(0, "end")
                self.exit_plate.insert(0, value)

        if detection_type in ("refc", "qr") and confidence >= 70.0:
            current_barcode = self.exit_barcode.get().strip()
            if current_barcode != value:
                self.exit_barcode.delete(0, "end")
                self.exit_barcode.insert(0, value)

    def _set_exit_barcode(self, value: str):
        self.exit_barcode.delete(0, "end")
        self.exit_barcode.insert(0, value)

    def _submit_exit(self):
        if self._waiting_capture:
            return

        qr_code = self.exit_barcode.get().strip()
        plate = self.exit_plate.get().strip()

        if not qr_code:
            messagebox.showwarning("Thieu du lieu", "Can co barcode de xu ly xe ra.")
            return

        self._waiting_capture = True
        self.btn_confirm_exit.configure(state="disabled")
        self.capture_status.configure(text="Vui long dung yen 2-3 giay de chup doi soat hinh anh...")
        self.after(2500, self._submit_exit_after_stable)

    def _submit_exit_after_stable(self):
        qr_code = self.exit_barcode.get().strip()
        plate = self.exit_plate.get().strip()
        lane = self.exit_lane.get().strip()

        local_image_base64 = self.exit_local_camera.get_latest_frame_base64()
        if not local_image_base64:
            self._waiting_capture = False
            self.btn_confirm_exit.configure(state="normal")
            self.capture_status.configure(text="Khong lay duoc anh local. Thu lai.")
            messagebox.showerror("Loi camera", "Khong lay duoc anh tu camera laptop de doi soat.")
            return

        result = ApiClient.process_exit(
            qr_code=qr_code,
            bien_so=plate,
            lane=lane,
            local_image_base64=local_image_base64,
        )
        self._waiting_capture = False
        self.btn_confirm_exit.configure(state="normal")
        self.capture_status.configure(text="Da xu ly xong luot xe ra.")

        if result is None:
            messagebox.showerror("Loi API", "Khong the ket noi backend de xu ly xe ra.")
            return

        self._render_result(result)

        if result.get("status") == "success" and result.get("decision") == "allow":
            self.hardware.open_barrier(lane=lane)
            messagebox.showinfo("Xe ra", "Xe ra hop le. Barrier da mo.")
            if callable(self.on_transaction_updated):
                self.on_transaction_updated()
        else:
            messagebox.showwarning("Can xac minh", result.get("message", "Can kiem tra thu cong."))

    def _render_result(self, data: dict):
        time_in = self._format_time(data.get("time_in"))
        time_out = self._format_time(data.get("time_out"))

        self.lbl_score.configure(
            text=(
                f"Tong khop: {data.get('similarity_score', 0)}% | "
                f"Chuoi: {data.get('string_similarity_score', '-')} | "
                f"Hinh: {data.get('image_similarity_score', '-')}"
            )
        )
        self.lbl_time_in.configure(text=f"Thoi gian vao: {time_in}")
        self.lbl_time_out.configure(text=f"Thoi gian ra: {time_out}")
        self.lbl_duration.configure(text=f"Thoi gian gui: {data.get('duration_minutes', '-') } phut")
        self.lbl_fee.configure(text=f"Phi gui xe: {data.get('fee', '-')}")
        self.lbl_owner.configure(text=f"Chu xe: {data.get('owner_name', '-')}")
        self.lbl_balance.configure(text=f"So du: {data.get('owner_balance', '-')}")
        self.lbl_lock.configure(text=f"Khoa xe: {'CO' if data.get('vehicle_locked') else 'KHONG'}")
        self.lbl_decision.configure(text=f"Quyet dinh: {data.get('decision', '-')}")
        self.lbl_message.configure(text=f"Thong diep: {data.get('message', '-')}")

        self._render_compare_images(data)

        lines = [
            f"Trang thai: {data.get('status', '-')}",
            f"Hanh dong: {data.get('action', '-')}",
            f"Bien so quet: {data.get('scanned_plate', '-')}",
            f"Bien so DB: {data.get('db_license_plate', '-')}",
            f"Ma giao dich: {data.get('transaction_id', '-')}",
            f"Thoi gian vao: {time_in}",
            f"Thoi gian ra: {time_out}",
            f"Alert bao ve: {data.get('alert_security', False)}",
            f"Thieu so du: {data.get('insufficient_balance', False)}",
            f"Mo cong (giay): {data.get('gate_open_seconds', 0)}",
            f"Anh vao IoT: {data.get('entry_iot_image_path', '-')}",
            f"Anh vao local: {data.get('entry_local_image_path', '-')}",
            f"Anh ra IoT: {data.get('exit_iot_image_path', '-')}",
            f"Anh ra local: {data.get('exit_local_image_path', '-')}",
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

    def _render_compare_images(self, data: dict):
        entry_path = data.get("entry_iot_image_path") or data.get("entry_local_image_path")
        exit_path = data.get("exit_iot_image_path") or data.get("exit_local_image_path")

        self._set_image_from_path(self.entry_image_label, entry_path, "Khong co anh vao de so sanh")
        self._set_image_from_path(self.exit_image_label, exit_path, "Khong co anh ra de so sanh")

    def _set_image_from_path(self, label: ctk.CTkLabel, image_path: str | None, missing_text: str):
        if not image_path:
            label.configure(image=None, text=missing_text)
            label.image = None
            return

        try:
            image = Image.open(image_path).convert("RGB")
            width = max(int(label.winfo_width() or 460), 300)
            height = max(int(label.winfo_height() or 160), 120)
            resized = image.resize((width, height))
            ctk_image = ctk.CTkImage(light_image=resized, dark_image=resized, size=(width, height))
            label.configure(image=ctk_image, text="")
            label.image = ctk_image
        except Exception:
            label.configure(image=None, text=f"Loi doc anh: {image_path}")
            label.image = None

    def _clear_form(self):
        self.exit_barcode.delete(0, "end")
        self.exit_plate.delete(0, "end")
        self.lbl_owner.configure(text="Chu xe: -")
        self.lbl_balance.configure(text="So du: -")
        self.lbl_lock.configure(text="Khoa xe: -")
        self.capture_status.configure(text="Dang quet bien so + REFC/QR bang khung do theo doi.")
        self.entry_image_label.configure(image=None, text="Chua co anh vao")
        self.entry_image_label.image = None
        self.exit_image_label.configure(image=None, text="Chua co anh ra")
        self.exit_image_label.image = None
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", "Chua co giao dich xe ra.")
        self.result_box.configure(state="disabled")

    def start_cameras(self):
        camera_id = int(os.getenv("LAPTOP_CAMERA_ID", "0"))
        self.exit_local_camera.start(camera_id=camera_id)
        self.exit_iot_camera.start()
        self._camera_running = True
        self.capture_status.configure(text="Camera xe ra dang hoat dong.")

    def stop_cameras(self):
        self.exit_local_camera.stop()
        self.exit_iot_camera.stop()
        self._camera_running = False
