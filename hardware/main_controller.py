import os
import glob
import requests
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message=r"You are using a Python version .* end of life.*",
    category=FutureWarning,
    module=r"google\.api_core\._python_version_support",
)

from google.cloud import vision

from app.services.fuzzy_matcher import gui_ve_main_controller, khoi_tao_db_mau

# =======================================================
# 1. CẤU HÌNH HỆ THỐNG
# =======================================================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
GOOGLE_KEY_PATH = BASE_DIR / "gg_cloud_key.json"
CAPTURE_DIR = PROJECT_ROOT / "capture"

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(GOOGLE_KEY_PATH)
ESP32_IP = "192.168.101.8"  # Thay bằng IP thực tế của ESP32 Nhật nhé
API_TOKEN = "ESP32_SECRET_KEY_2025"
THRESHOLD = 70  # Độ khớp trên 70% theo yêu cầu của Nhật

# =======================================================
# 2. HÀM RA LỆNH MỞ CỔNG (Gửi tín hiệu tới ESP32)
# =======================================================
def ra_lenh_mo_cong():
    url = f"http://{ESP32_IP}/open?token={API_TOKEN}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("[CMD] Barrier open command sent successfully.")
            return True
        else:
            print(f"[CMD] Failed with status code: {response.status_code}")
    except Exception as e:
        print(f"[CMD] Cannot connect to ESP32: {e}")
    return False


def nhan_ket_qua_tu_fuzzy(ocr_text: str, ket_qua: dict):
    """Nhan ket qua fuzzy tu fuzzy_matcher va xu ly hanh dong barrier."""
    best_match = ket_qua.get("bien_so")
    score = ket_qua.get("ty_le", 0)
    print(f"[MATCH] Highest score: {score}% with plate '{best_match}'")

    if ket_qua.get("hople"):
        info = ket_qua.get("thong_tin") or {}
        print("[INFO] Vehicle is valid.")
        print(f"   - Owner: {info.get('chu_xe', '-')}")
        print(f"   - StudentId: {info.get('mssv', '-')}")
        print("   - Status: opening barrier...")
        mo_cong = ra_lenh_mo_cong()
        return {
            "ocr": ocr_text,
            "ket_qua": ket_qua,
            "barrier_opened": mo_cong,
        }

    print("[INFO] Vehicle not found or image quality too low.")
    return {
        "ocr": ocr_text,
        "ket_qua": ket_qua,
        "barrier_opened": False,
    }

# =======================================================
# 3. QUY TRÌNH XỬ LÝ CHÍNH
# =======================================================
def xu_ly_xe_vao():
    # Bước 1: Tìm ảnh mới nhất trong folder capture
    capture_pattern_jpg = str(CAPTURE_DIR / "*.jpg")
    capture_pattern_png = str(CAPTURE_DIR / "*.png")
    list_of_files = glob.glob(capture_pattern_jpg) + glob.glob(capture_pattern_png)
    if not list_of_files:
        print("[INFO] capture folder is empty.")
        return

    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"\n[INFO] Processing image: {latest_file}")

    # Bước 2: Gọi Google Cloud Vision đọc biển số
    client = vision.ImageAnnotatorClient()
    with open(latest_file, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    
    if not response.text_annotations:
        print("[WARN] No text detected from image.")
        return

    ocr_text = response.text_annotations[0].description.strip()
    print(f"[OCR] Google text: '{ocr_text}'")

    # Bước 3 + 4: So khớp fuzzy và gửi kết quả về main_controller receiver.
    return gui_ve_main_controller(
        ocr_result=ocr_text,
        threshold=THRESHOLD,
        db_path="parking.db",
        receiver=nhan_ket_qua_tu_fuzzy,
    )

if __name__ == '__main__':
    # Khởi tạo DB mẫu nếu chưa có (thay cho database_helper cũ).
    khoi_tao_db_mau(db_path="parking.db")
    
    print("[INFO] Main controller is listening for new images...")
    # Trong thực tế Nhật có thể cho chạy vòng lặp để kiểm tra folder liên tục
    xu_ly_xe_vao()