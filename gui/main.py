from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env", override=True)

if __package__:
    from .app_window import MainApp
else:
    from app_window import MainApp

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
