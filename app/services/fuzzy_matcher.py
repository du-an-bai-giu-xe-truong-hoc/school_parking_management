import re
import sqlite3
import importlib
import warnings
from typing import Callable, Optional

from thefuzz import fuzz


def chuan_hoa_bien_so(text):
    """Normalize plate string before matching."""
    if not text:
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def kiem_tra_xe_hop_le(ocr_result, threshold=80, db_path="parking.db"):
    """Return matching result for OCR plate against registered vehicles."""
    ocr_clean = chuan_hoa_bien_so(ocr_result)
    print(f"[OCR] normalized: '{ocr_clean}'")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT bien_so, chu_xe, mssv FROM xe_dang_ky")
    danh_sach_xe = cursor.fetchall()
    conn.close()

    best_match = None
    best_score = 0
    xe_info = None

    for db_plate, chu_xe, mssv in danh_sach_xe:
        db_plate_clean = chuan_hoa_bien_so(db_plate)
        score = fuzz.ratio(ocr_clean, db_plate_clean)

        if score > best_score:
            best_score = score
            best_match = db_plate
            xe_info = {"chu_xe": chu_xe, "mssv": mssv}

    if best_score >= threshold:
        print(
            f"[OK] match: {best_match} (score: {best_score}%) - owner: {xe_info['chu_xe']}"
        )
        return {
            "hople": True,
            "bien_so": best_match,
            "ty_le": best_score,
            "thong_tin": xe_info,
        }

    print(
        f"[NO] best candidate: {best_match}, score: {best_score}% (required >= {threshold}%)"
    )
    return {
        "hople": False,
        "bien_so": best_match,
        "ty_le": best_score,
        "thong_tin": None,
    }


def _load_main_controller_receiver() -> Optional[Callable[[str, dict], object]]:
    """Load main controller receiver lazily to avoid hard circular imports."""
    main_controller = None
    for module_name in ("hardware.main_controller", "main_controller"):
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"You are using a Python version .* end of life.*",
                    category=FutureWarning,
                    module=r"google\.api_core\._python_version_support",
                )
                main_controller = importlib.import_module(module_name)
            break
        except Exception:
            continue

    if main_controller is None:
        return None

    receiver = getattr(main_controller, "nhan_ket_qua_tu_fuzzy", None)
    if callable(receiver):
        return receiver
    return None


def gui_ve_main_controller(
    ocr_result,
    threshold=80,
    db_path="parking.db",
    receiver: Optional[Callable[[str, dict], object]] = None,
):
    """Run fuzzy matching then forward result to main_controller receiver."""
    ket_qua = kiem_tra_xe_hop_le(ocr_result=ocr_result, threshold=threshold, db_path=db_path)

    target_receiver = receiver or _load_main_controller_receiver()
    if callable(target_receiver):
        target_receiver(ocr_result, ket_qua)
    else:
        print("[WARN] Khong tim thay receiver trong main_controller.")

    return ket_qua


def khoi_tao_db_mau(db_path="parking.db"):
    """Create sample registration table/data for local testing."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS xe_dang_ky (
            id INTEGER PRIMARY KEY,
            bien_so TEXT,
            chu_xe TEXT,
            mssv TEXT
        )
        """
    )

    cursor.execute("SELECT COUNT(*) FROM xe_dang_ky")
    if cursor.fetchone()[0] == 0:
        du_lieu_mau = [
            ("43F1-123.45", "Minh Nhat", "23SPT01"),
            ("92B1-567.89", "Sinh vien A", "23SPT02"),
            ("29A-999.99", "Giang vien B", "GV001"),
        ]
        cursor.executemany(
            "INSERT INTO xe_dang_ky (bien_so, chu_xe, mssv) VALUES (?, ?, ?)", du_lieu_mau
        )
        conn.commit()

    conn.close()


if __name__ == "__main__":
    khoi_tao_db_mau()

    print("\n--- TEST 1: OCR typo and spaces ---")
    gui_ve_main_controller("43F1 123.4S")

    print("\n--- TEST 2: Unknown plate ---")
    gui_ve_main_controller("43F1 999.99")