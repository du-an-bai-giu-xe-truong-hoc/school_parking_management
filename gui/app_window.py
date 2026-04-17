from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

if (__package__ or "").startswith("gui"):
    from .pages.dashboard_page import DashboardPage
    from .pages.log_history_page import LogHistoryPage
    from .pages.xe_ra_page import XeRaPage
    from .pages.xe_vao_page import XeVaoPage
    from .styles import AppStyle
else:
    from pages.dashboard_page import DashboardPage
    from pages.log_history_page import LogHistoryPage
    from pages.xe_ra_page import XeRaPage
    from pages.xe_vao_page import XeVaoPage
    from styles import AppStyle


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        AppStyle.apply()
        self.title("School Parking Management")
        self.geometry("1450x920")
        self.minsize(1200, 760)

        self.header = ctk.CTkFrame(self, height=64, fg_color=AppStyle.PRIMARY)
        self.header.pack(fill="x", padx=0, pady=0)
        self.header.pack_propagate(False)

        ctk.CTkLabel(
            self.header,
            text="SPM",
            font=("Helvetica", 24, "bold"),
            text_color="white",
        ).pack(side="left", padx=(16, 8))
        ctk.CTkLabel(
            self.header,
            text="School Parking Management",
            font=("Helvetica", 21, "bold"),
            text_color="white",
        ).pack(side="left")

        self.time_label = ctk.CTkLabel(self.header, text="", font=("Helvetica", 14), text_color="white")
        self.time_label.pack(side="right", padx=20)
        self._update_time()

        ctk.CTkButton(
            self.header,
            text="Bao dong",
            fg_color=AppStyle.DANGER,
            hover_color="#dc2626",
            width=120,
            command=self.show_alert,
        ).pack(side="right", padx=8)

        self.tabview = ctk.CTkTabview(self, fg_color="transparent")
        self.tabview.pack(fill="both", expand=True, padx=12, pady=12)

        self.tabview.add("Xe Vao")
        self.tabview.add("Xe Ra")
        self.tabview.add("Log History")
        self.tabview.add("Thong Tin")

        self.xe_vao_page = XeVaoPage(
            self.tabview.tab("Xe Vao"),
            self,
            on_transaction_updated=self._refresh_data_views,
        )
        self.xe_vao_page.pack(fill="both", expand=True)

        self.xe_ra_page = XeRaPage(
            self.tabview.tab("Xe Ra"),
            self,
            on_transaction_updated=self._refresh_data_views,
        )
        self.xe_ra_page.pack(fill="both", expand=True)

        self.log_history_page = LogHistoryPage(self.tabview.tab("Log History"), self)
        self.log_history_page.pack(fill="both", expand=True)

        self.dashboard_page = DashboardPage(self.tabview.tab("Thong Tin"), self)
        self.dashboard_page.pack(fill="both", expand=True)

        self._refresh_data_views()
        self.xe_ra_page.stop_cameras()

        self._active_tab = self.tabview.get()
        self.after(250, self._watch_tab_change)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _refresh_data_views(self):
        for page in (self.log_history_page, self.dashboard_page):
            refresh = getattr(page, "refresh_data", None)
            if callable(refresh):
                refresh()

    def _watch_tab_change(self):
        if not self.winfo_exists():
            return

        current_tab = self.tabview.get()
        if current_tab != self._active_tab:
            self._handle_tab_change(current_tab)
            self._active_tab = current_tab

        self.after(250, self._watch_tab_change)

    def _handle_tab_change(self, current_tab: str):
        if current_tab == "Xe Ra":
            self.xe_ra_page.stop_cameras()
            self.xe_vao_page.begin_exit_transition(3, on_complete=self.xe_ra_page.start_cameras)
            return

        self.xe_vao_page.cancel_transition()
        self.xe_ra_page.stop_cameras()
        if current_tab == "Xe Vao":
            self.xe_vao_page.start_cameras()
        else:
            self.xe_vao_page.stop_cameras()

    def _on_close(self):
        try:
            self.xe_vao_page.cancel_transition()
            self.xe_vao_page.stop_cameras()
            self.xe_ra_page.stop_cameras()
        finally:
            self.destroy()

    def _update_time(self):
        self.time_label.configure(text=datetime.now().strftime("%H:%M:%S | %d/%m/%Y"))
        self.after(1000, self._update_time)

    def show_alert(self):
        messagebox.showwarning("Bao dong", "Da gui tin hieu bao dong cho bo phan bao ve.")
