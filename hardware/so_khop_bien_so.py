import re
import sqlite3

from thefuzz import fuzz


def chuan_hoa_bien_so(text):
    """Normalize a license plate string for comparison."""
    if not text:
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def kiem_tra_xe_trong_db(ocr_text, threshold=85, db_path="parking_database.db"):
    """Compare OCR text against registered plates in SQLite DB.

    Returns: (is_valid, best_match_plate, similarity_score)
    """
    ocr_cleaned = chuan_hoa_bien_so(ocr_text)
    print(f"[*] OCR normalized: '{ocr_cleaned}'")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT bien_so FROM xe_dang_ky")
    danh_sach_xe = cursor.fetchall()
    conn.close()

    best_match = None
    highest_score = 0

    print("[*] Calculating fuzzy match score...")
    for (db_plate,) in danh_sach_xe:
        db_plate_cleaned = chuan_hoa_bien_so(db_plate)
        score = fuzz.ratio(ocr_cleaned, db_plate_cleaned)

        if score > highest_score:
            highest_score = score
            best_match = db_plate

    if highest_score >= threshold:
        print(
            f"[OK] Matched '{best_match}' in DB (score: {highest_score}%, threshold: {threshold}%)"
        )
        return True, best_match, highest_score

    print(
        f"[NO] Best candidate '{best_match}' scored {highest_score}% (threshold: {threshold}%)"
    )
    return False, best_match, highest_score


def khoi_tao_database_mau(db_path="parking_database.db"):
    """Create sample table/data for local checks."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS xe_dang_ky (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bien_so TEXT NOT NULL
        )
        """
    )

    cursor.execute("SELECT COUNT(*) FROM xe_dang_ky")
    if cursor.fetchone()[0] == 0:
        xe_mau = [("43F1-123.45",), ("92B1-567.89",), ("29A-999.99",)]
        cursor.executemany("INSERT INTO xe_dang_ky (bien_so) VALUES (?)", xe_mau)
        conn.commit()

    conn.close()


if __name__ == "__main__":
    khoi_tao_database_mau()

    print("--- CHECK 1: Small OCR typo ---")
    kiem_tra_xe_trong_db("43F1 123.4S")

    print("\n--- CHECK 2: Unknown plate ---")
    kiem_tra_xe_trong_db("92B1-111.11")
