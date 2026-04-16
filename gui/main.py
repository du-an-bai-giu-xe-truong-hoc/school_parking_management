# gui/main.py
import logging
import os
from app_window import MainApp

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    logging.info("🚀 Khởi động GUI Quản Lý Bãi Xe")
    app = MainApp()
    app.mainloop()
