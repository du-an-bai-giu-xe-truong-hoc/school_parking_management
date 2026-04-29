from datetime import datetime
from tkinter import ttk

import customtkinter as ctk

if (__package__ or "").startswith("gui"):
    from ..styles import AppStyle
    from ..utils.api_client import ApiClient
else:
    from styles import AppStyle
    from utils.api_client import ApiClient


class LogHistoryPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="transparent")
        self.main_app = main_app

        container = ctk.CTkFrame(self, fg_color=AppStyle.CARD_BG, corner_radius=12)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 8))

        ctk.CTkLabel(
            header,
            text="Log history xe ra vao",
            font=("Helvetica", 18, "bold"),
            text_color=AppStyle.PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(header, text="Lam moi", width=100, command=self.refresh_data).pack(side="right")

        columns = (
            "transaction_id",
            "license_plate",
            "owner_name",
            "identity_card",
            "owner_balance",
            "vehicle_type",
            "time_in",
            "time_out",
            "status",
            "fee",
            "lane",
            "image_similarity_score",
            "alert_flag",
        )

        table_frame = ctk.CTkFrame(container, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=130)

        self.tree.column("owner_name", width=180)
        self.tree.column("owner_balance", width=130)
        self.tree.column("time_in", width=165)
        self.tree.column("time_out", width=165)
        self.tree.column("image_similarity_score", width=150)
        self.tree.column("alert_flag", width=110)

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.status_label = ctk.CTkLabel(container, text="", text_color="#475569", font=("Helvetica", 12))
        self.status_label.pack(anchor="w", padx=12, pady=(0, 10))

    def refresh_data(self):
        history = ApiClient.get_parking_history(limit=500)
        if history is None:
            self.status_label.configure(
                text=(
                    "Khong the lay du lieu history tu backend. "
                    "Hay chay run_api.ps1 hoac kiem tra FASTAPI_URL/FASTAPI_PREFIX trong file .env"
                ),
                text_color="#B45309",
            )
            return

        for row in self.tree.get_children():
            self.tree.delete(row)

        for item in history:
            self.tree.insert(
                "",
                "end",
                values=(
                    item.get("transaction_id", "-"),
                    item.get("license_plate", "-"),
                    item.get("owner_name", "-"),
                    item.get("identity_card", "-"),
                    item.get("owner_balance", "-"),
                    item.get("vehicle_type", "-"),
                    self._format_datetime(item.get("time_in")),
                    self._format_datetime(item.get("time_out")),
                    item.get("status", "-"),
                    item.get("fee", "-"),
                    item.get("lane", "-"),
                    item.get("image_similarity_score", "-"),
                    item.get("alert_flag", False),
                ),
            )

        self.status_label.configure(
            text=f"Da tai {len(history)} ban ghi.",
            text_color="#15803D",
        )

    def _format_datetime(self, value):
        if not value:
            return "-"
        if isinstance(value, datetime):
            return value.strftime("%H:%M:%S %d/%m/%Y")
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed.strftime("%H:%M:%S %d/%m/%Y")
            except ValueError:
                return value
        return str(value)
