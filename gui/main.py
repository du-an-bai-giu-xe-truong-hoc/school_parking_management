# gui/main.py
import customtkinter as ctk
from dotenv import load_dotenv
from app_window import MainApp

if __name__ == "__main__":
    load_dotenv()
    app = MainApp()
    app.mainloop()
