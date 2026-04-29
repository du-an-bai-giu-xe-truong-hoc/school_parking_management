import os
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import requests

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Địa chỉ IP của ESP32-CAM (Lấy từ Serial Monitor hoặc Web)
ESP32_BASE_URL = os.getenv("ESP32_BASE_URL", "http://192.168.81.61").rstrip("/")
BACKEND_UPLOAD_URL = os.getenv("BACKEND_UPLOAD_URL", "http://localhost:8000/api/camera/esp32/upload").strip()
CAPTURE_DIR = Path(os.getenv("CAPTURE_DIR", str(PROJECT_ROOT / "capture")))

# Danh sách endpoint có thể dùng để đọc trạng thái IR sensor.
# Script sẽ thử lần lượt cho đến khi endpoint nào phản hồi hợp lệ.
SENSOR_ENDPOINTS = [
    "/ir-status",
    "/sensor",
    "/status",
]

# Polling mặc định 200ms để phản ứng nhanh nhưng không quá tải mạng.
POLL_INTERVAL_SECONDS = 0.2

def check_connection():
    print(f"⏳ Đang thử kết nối tới ESP32-CAM tại {ESP32_BASE_URL}...")
    
    try:
        # Gọi vào đường dẫn /status để xem mạch có phản hồi không
        response = requests.get(f"{ESP32_BASE_URL}/status", timeout=5)
        
        if response.status_code == 200:
            print("✅ Đã kết nối được với ESP32-CAM thành công!")
            data = response.json()
            print(f"📊 Trạng thái hệ thống: WiFi RSSI {data.get('wifi_rssi')}dBm, RAM rảnh: {data.get('free_heap')} bytes")
            return True
        else:
            print(f"⚠️ Trả về mã lỗi: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print("❌ Không thể kết nối. Hãy kiểm tra lại xem máy tính và ESP32 đã chung WiFi chưa.")
        return False


def _parse_ir_state(payload):
    """Trả về True/False nếu đọc được trạng thái IR, ngược lại trả về None."""
    if isinstance(payload, dict):
        for key in (
            "ir",
            "ir_state",
            "ir_sensor",
            "ir_detected",
            "triggered",
            "motion",
            "car_present",
        ):
            if key in payload:
                value = payload[key]
                if isinstance(value, bool):
                    return value
                if isinstance(value, (int, float)):
                    return int(value) == 1
                if isinstance(value, str):
                    return value.strip().lower() in {"1", "true", "on", "active", "detected"}
    if isinstance(payload, str):
        return payload.strip().lower() in {"1", "true", "on", "active", "detected"}
    return None


def read_ir_state():
    """Đọc trạng thái IR từ ESP32. Trả về True/False hoặc None nếu chưa đọc được."""
    for endpoint in SENSOR_ENDPOINTS:
        try:
            response = requests.get(f"{ESP32_BASE_URL}{endpoint}", timeout=2)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                state = _parse_ir_state(response.json())
            else:
                state = _parse_ir_state(response.text)

            if state is not None:
                return state
        except requests.RequestException:
            continue
        except ValueError:
            continue
    return None


def _save_latest_image(image_bytes):
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"cam_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    filepath = CAPTURE_DIR / filename
    filepath.write_bytes(image_bytes)
    return filepath


def _upload_capture_to_backend(image_path: Path):
    if not BACKEND_UPLOAD_URL:
        print("⚠️ BACKEND_UPLOAD_URL rỗng, bỏ qua upload backend.")
        return False

    try:
        with image_path.open("rb") as fh:
            files = {"file": (image_path.name, fh, "image/jpeg")}
            response = requests.post(BACKEND_UPLOAD_URL, files=files, timeout=12)
        response.raise_for_status()
        print(f"📤 Đã upload ảnh lên backend: {BACKEND_UPLOAD_URL}")
        return True
    except requests.exceptions.RequestException as exc:
        print(f"❌ Upload backend thất bại: {exc}")
        return False


def _fetch_latest_image_bytes():
    """Luôn ưu tiên endpoint /latest theo yêu cầu tích hợp backend."""
    latest_url = f"{ESP32_BASE_URL}/latest"
    response = requests.get(latest_url, timeout=8)
    response.raise_for_status()

    image_bytes = response.content or b""
    if not image_bytes:
        raise RuntimeError("Endpoint /latest trả về rỗng")

    content_type = (response.headers.get("Content-Type") or "").lower()
    if "image" not in content_type and not image_bytes.startswith(b"\xff\xd8"):
        raise RuntimeError("/latest không trả dữ liệu ảnh hợp lệ")

    return image_bytes


def capture_on_trigger(show_image=False):
    """Khi có trigger: lấy ảnh từ /latest, lưu capture/, rồi upload lên backend."""
    print("📷 IR kích hoạt, đang lấy ảnh mới nhất từ ESP32-CAM (/latest)...")
    try:
        image_bytes = _fetch_latest_image_bytes()

        saved_path = _save_latest_image(image_bytes)
        print(f"✅ Đã lưu ảnh tự động: {saved_path}")
        _upload_capture_to_backend(saved_path)

        if show_image:
            img_array = np.array(bytearray(image_bytes), dtype=np.uint8)
            img = cv2.imdecode(img_array, -1)
            if img is not None:
                cv2.imshow("ESP32-CAM Live View", img)
                cv2.waitKey(1)
            else:
                print("⚠️ Ảnh đã lưu nhưng không render được bằng OpenCV.")

    except Exception as e:
        print("❌ Lỗi khi chụp ảnh:", e)


def _is_verified_ir_trigger(current_state, last_state: bool) -> bool:
    """Xác minh trigger bằng bool: chỉ hợp lệ khi có cạnh lên 0->1."""
    current_bool = bool(current_state)
    return current_bool and (not bool(last_state))

def monitor_ir_and_capture(show_image=False):
    """Theo dõi tín hiệu IR và tự chụp ảnh khi có cạnh kích hoạt."""
    print("🛰️ Bắt đầu theo dõi IR sensor. Nhấn Ctrl+C để dừng.")
    print(f"🔎 Các endpoint được thử: {', '.join(SENSOR_ENDPOINTS)}")

    last_state = False
    while True:
        current_state = read_ir_state()

        # Nếu chưa đọc được trạng thái, chờ và thử lại.
        if current_state is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        # Dùng bool để xác minh tín hiệu IR hợp lệ trước khi chụp + gửi app/main.py.
        if _is_verified_ir_trigger(current_state=current_state, last_state=last_state):
            capture_on_trigger(show_image=show_image)

        last_state = current_state
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    # 1. Kiểm tra kết nối trước
    if check_connection():
        try:
            # 2. Nếu kết nối OK thì theo dõi cảm biến IR để tự động chụp
            monitor_ir_and_capture(show_image=False)
        except KeyboardInterrupt:
            print("\n🛑 Đã dừng theo dõi IR sensor.")
            cv2.destroyAllWindows()