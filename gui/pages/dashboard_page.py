from datetime import datetime
from tkinter import ttk

import customtkinter as ctk

if (__package__ or "").startswith("gui"):
    from ..styles import AppStyle
    from ..utils.api_client import ApiClient
else:
    from styles import AppStyle
    from utils.api_client import ApiClient

class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="transparent")
        self.main_app = main_app

        self._build_summary_cards()
        self._build_active_table()

    def _build_summary_cards(self):
        card_row = ctk.CTkFrame(self, fg_color="transparent")
        card_row.pack(fill="x", padx=15, pady=(12, 8))
        card_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.card_active = self._create_card(card_row, "Xe dang do", "0", 0)
        self.card_completed = self._create_card(card_row, "Luot ra hom nay", "0", 1)
        self.card_total = self._create_card(card_row, "Tong giao dich hom nay", "0", 2)

    def _create_card(self, parent, title: str, initial_value: str, col: int):
        card = ctk.CTkFrame(parent, fg_color=AppStyle.CARD_BG, corner_radius=12)
        card.grid(row=0, column=col, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=("Helvetica", 15, "bold"), text_color="#334155").pack(
            pady=(12, 4)
        )
        value_label = ctk.CTkLabel(card, text=initial_value, font=("Helvetica", 30, "bold"), text_color=AppStyle.PRIMARY)
        value_label.pack(pady=(0, 14))
        return value_label

    def _build_active_table(self):
        table_container = ctk.CTkFrame(self, fg_color=AppStyle.CARD_BG, corner_radius=12)
        table_container.pack(fill="both", expand=True, padx=15, pady=(8, 15))

        header = ctk.CTkFrame(table_container, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(
            header,
            text="Danh sach xe dang do trong bai",
            font=("Helvetica", 16, "bold"),
            text_color=AppStyle.PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(header, text="Lam moi", width=100, command=self.refresh_data).pack(side="right")

        columns = (
            "transaction_id",
            "license_plate",
            "owner_name",
            "identity_card",
            "vehicle_type",
            "time_in",
            "status",
        )

        table_frame = ctk.CTkFrame(table_container, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=140)

        self.tree.column("owner_name", width=180)
        self.tree.column("time_in", width=170)
        self.tree.column("status", width=100)

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")

    def refresh_data(self):
        history = ApiClient.get_parking_history(limit=500) or []
        active = ApiClient.get_active_transactions(limit=500) or []

        today = datetime.now().date()
        completed_today = 0
        total_today = 0

        for item in history:
            time_in_raw = item.get("time_in")
            time_in = self._parse_datetime(time_in_raw)
            if time_in and time_in.date() == today:
                total_today += 1
                if str(item.get("status", "")).lower() == "completed":
                    completed_today += 1

        self.card_active.configure(text=str(len(active)))
        self.card_completed.configure(text=str(completed_today))
        self.card_total.configure(text=str(total_today))

        for row in self.tree.get_children():
            self.tree.delete(row)

        for item in active:
            self.tree.insert(
                "",
                "end",
                values=(
                    item.get("transaction_id", "-"),
                    item.get("license_plate", "-"),
                    item.get("owner_name", "-"),
                    item.get("identity_card", "-"),
                    item.get("vehicle_type", "-"),
                    self._format_datetime(item.get("time_in")),
                    item.get("status", "-"),
                ),
            )

    def _parse_datetime(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    def _format_datetime(self, value):
        parsed = self._parse_datetime(value)
        if parsed is None:
            return "-"
        return parsed.strftime("%H:%M:%S %d/%m/%Y")
