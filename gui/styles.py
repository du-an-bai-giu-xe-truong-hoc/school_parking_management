# gui/styles.py
import customtkinter as ctk

class AppStyle:
    PRIMARY = "#1E3A8A"      # Navy header
    SUCCESS = "#10B981"
    DANGER = "#EF4444"       # Đỏ cảnh báo
    WARNING = "#F59E0B"
    BG = "#F8FAFC"
    FG = "#0F172A"
    CARD_BG = "#FFFFFF"
    TEXT_DARK = "#1E2937"

    @staticmethod
    def apply():
        ctk.set_appearance_mode("light")   # Ảnh bạn gửi là light theme
        ctk.set_default_color_theme("blue")
        return {
            "title": ("Helvetica", 20, "bold"),
            "subtitle": ("Helvetica", 16, "bold"),
            "body": ("Helvetica", 13),
            "button": ("Helvetica", 14, "bold"),
        }
