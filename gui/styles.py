# gui/styles.py
import customtkinter as ctk

class AppStyle:
    """Theme khớp 100% ảnh giao diện bạn cung cấp"""
    PRIMARY = "#1E3A8A"      # Header xanh đậm
    ACCENT = "#3B82F6"
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"
    BG_DARK = "#0F172A"
    TEXT_LIGHT = "#F1F5F9"
    TEXT_GRAY = "#64748B"
    FONT_TITLE = ("Helvetica", 20, "bold")
    FONT_SUBTITLE = ("Helvetica", 14)

    @staticmethod
    def apply_theme():
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
