# gui/styles.py
import customtkinter as ctk

class AppStyle:
    """Theme và style chung cho toàn bộ GUI (đã sửa subtitle, title, font...)"""

    # Màu sắc theo ảnh bạn cung cấp
    PRIMARY = "#1E3A8A"
    SUCCESS = "#10B981"
    DANGER = "#EF4444"
    WARNING = "#F59E0B"
    CARD_BG = "#FFFFFF"
    TEXT_DARK = "#1E2937"

    # Font (đây là phần bị thiếu trước đó)
    TITLE_FONT = ("Helvetica", 20, "bold")
    SUBTITLE_FONT = ("Helvetica", 16, "bold")
    BODY_FONT = ("Helvetica", 13)
    BUTTON_FONT = ("Helvetica", 14, "bold")

    @staticmethod
    def apply():
        """Áp dụng theme light (giống ảnh bạn gửi)"""
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
