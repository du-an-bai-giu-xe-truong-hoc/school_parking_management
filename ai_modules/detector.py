import cv2
import numpy as np
import re
import os
from google.cloud import vision
from ultralytics import YOLO

# ---------------------------------------------------------
# [1. KHỞI TẠO VŨ KHÍ & QUYỀN TRUY CẬP]
# ---------------------------------------------------------
# Sensei! NHỚ THAY ĐỔI ĐƯỜNG DẪN FILE JSON NÀY. Đừng để trống!
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"D:\Python_Code\AI_Project\school_parking_management\core\mvbl-492911-81f79d8de732.json"

try:
    # Nhớ dùng file best.pt đã huấn luyện nhận diện biển số của ngài
    plate_detector = YOLO(r'D:\Python_Code\AI_Project\school_parking_management\ai_modules\best.pt') 
    vision_client = vision.ImageAnnotatorClient()
    print("[VALKYRIE] Vũ khí và hệ thống tình báo đã sẵn sàng.")
except Exception as e:
    print(f"[LỖI NGHIÊM TRỌNG] Không thể khởi tạo hệ thống: {e}")
    exit()

# ---------------------------------------------------------
# [2. BỘ LỌC NGHIỆP VỤ]
# ---------------------------------------------------------
def is_motorcycle_plate(text: str) -> bool:
    """Bộ lọc kiểm duyệt: Chỉ xác nhận biển số xe máy Việt Nam"""
    clean_text = re.sub(r'[^A-Z0-9]', '', text.upper())
    if not (7 <= len(clean_text) <= 9):
        return False
    # Biểu thức kiểm tra cơ bản (ví dụ: 43K112345)
    pattern = r'^\d{2}[A-Z]{1,2}\d{4,5}$'
    return bool(re.match(pattern, clean_text))

def format_plate_text(raw_text: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', raw_text.upper())

def process_plate_ocr(plate_crop) -> dict:
    """Gửi ảnh đã cắt lên Google Cloud Vision"""
    is_success, buffer = cv2.imencode(".jpg", plate_crop)
    if not is_success:
        return {"status": "error", "message": "Lỗi đóng gói ảnh."}
    
    gcv_image = vision.Image(content=buffer.tobytes())
    response = vision_client.text_detection(image=gcv_image)
    
    if response.error.message:
        return {"status": "error", "message": response.error.message}
    if not response.text_annotations:
        return {"status": "error", "message": "Không đọc được chữ nào."}
        
    raw_text = response.text_annotations[0].description.strip()
    
    if is_motorcycle_plate(raw_text):
        return {"status": "success", "plate_number": format_plate_text(raw_text), "raw": raw_text}
    else:
        return {"status": "rejected", "message": "Không đúng chuẩn xe máy.", "raw": raw_text}

# ---------------------------------------------------------
# [3. CHIẾN DỊCH GIÁM SÁT THỜI GIAN THỰC (WEBCAM)]
# ---------------------------------------------------------
def live_surveillance():
    print("[VALKYRIE] Đang kết nối với Camera... (Bấm 'Q' để thoát, 'C' để chụp và quét)")
    cap = cv2.VideoCapture(0) # 0 là camera mặc định của laptop
    
    if not cap.isOpened():
        print("[CẢNH BÁO] Không thể chiếm quyền điều khiển Camera!")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[CẢNH BÁO] Mất tín hiệu từ Camera.")
            break

        # Đưa khung hình cho YOLO trinh sát
        results = plate_detector(frame, verbose=False)
        
        # Biến lưu trữ tọa độ biển số (nếu có)
        current_plate_box = None

        if results and len(results[0].boxes) > 0:
            # Lấy mục tiêu rõ ràng nhất
            box = results[0].boxes[0]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            current_plate_box = (x1, y1, x2, y2)
            
            # Vẽ khung đỏ lên màn hình để Sensei ngắm
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame, "MUC TIEU", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Hiển thị màn hình giám sát
        cv2.imshow("Valkyrie Live Surveillance", frame)

        # Chờ lệnh từ bàn phím (1 milliseconds)
        key = cv2.waitKey(1) & 0xFF
        
        # Lệnh RÚT LUI
        if key == ord('q'):
            print("[VALKYRIE] Kết thúc chiến dịch giám sát.")
            break
            
        # Lệnh KHAI HỎA (Quét chữ)
        elif key == ord('c'):
            if current_plate_box is not None:
                print("\n[VALKYRIE] Đã khóa mục tiêu! Đang gửi lên Cloud...")
                x1, y1, x2, y2 = current_plate_box
                plate_crop = frame[y1:y2, x1:x2]
                
                # Hiển thị ảnh cắt ra để kiểm tra
                cv2.imshow("Plate Crop", plate_crop)
                
                result = process_plate_ocr(plate_crop)
                print(f"-> Trạng thái : {result['status'].upper()}")
                if result['status'] == 'success':
                    print(f"-> Biển số    : {result.get('plate_number')}")
                else:
                    print(f"-> Thông báo  : {result.get('message')}")
                print(f"-> Dữ liệu thô: {result.get('raw')}\n")
            else:
                print("[CẢNH BÁO] Không có mục tiêu trong tầm ngắm. Hãy đợi YOLO nhận diện!")

    # Dọn dẹp hiện trường
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    live_surveillance()
