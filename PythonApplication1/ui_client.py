import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import serial
import os
from dotenv import load_dotenv
import datetime
import json

# Load các thông số từ file .env
load_dotenv()

app = FastAPI()

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG TỪ BIẾN MÔI TRƯỜNG
# ==========================================
DB_API_BASE_URL = os.getenv("DB_API_BASE_URL", "http://127.0.0.1:5000/api") 
ARDUINO_PORT = os.getenv("ARDUINO_PORT", "COM3")                             
BAUD_RATE = int(os.getenv("BAUD_RATE", 9600))

# Khởi tạo kết nối Serial với Barie
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    print(f"Đã kết nối Barie tại {ARDUINO_PORT}.")
except Exception as e:
    print(f"Cảnh báo phần cứng: Không thể kết nối {ARDUINO_PORT}. Lỗi: {e}")
    arduino = None

class CameraData(BaseModel):
    qr_code: str
    bien_so: str = "" 
    gate_type: str

# Hàm tính phí gửi xe theo thời gian thực
def tinh_phi_gui_xe():
    now = datetime.datetime.now()
    thu_trong_tuan = now.weekday() # Thứ 2 là 0, Chủ nhật là 6
    gio_hien_tai = now.hour
    
    # Từ Thứ 2 (0) đến Thứ 7 (5), và từ 5h00 đến 16h59 (nhỏ hơn 17)
    if 0 <= thu_trong_tuan <= 5 and 5 <= gio_hien_tai < 17:
        return 1000
    else:
        return 2000

# ==========================================
# 2. LOGIC ĐIỀU PHỐI TRUNG TÂM
# ==========================================
async def hamanlinkcmtrequest(qr_code: str, gate_type: str, bien_so: str):
    """
    Hàm xử lý cốt lõi. Đã được chia nhánh Xe Vào / Xe Ra.
    TUYỆT ĐỐI KHÔNG ĐỔI TÊN HÀM NÀY KHI BẢO TRÌ.
    """
    async with httpx.AsyncClient() as client:
        # --- BƯỚC 1: KIỂM TRA MÃ CƠ BẢN ---
        try:
            check_response = await client.get(f"{DB_API_BASE_URL}/check-qr?code={qr_code}", timeout=5.0)
            if check_response.status_code != 200:
                return {"status": "error", "message": "Lỗi kết nối DB Server."}
            
            # Bổ sung try-except chống lỗi sập app nếu DB trả về HTML thay vì JSON
            try:
                xe_info = check_response.json()
            except json.JSONDecodeError:
                return {"status": "error", "message": "Lỗi định dạng dữ liệu từ Server (Không phải JSON)."}
                
        except httpx.RequestError as e:
            return {"status": "error", "message": f"Mất kết nối DB: {str(e)}"}

        if not xe_info.get("exists"):
            return {"status": "rejected", "message": "Mã không tồn tại."}
        
        if xe_info.get("status") != "Active":
            return {"status": "rejected", "message": "Xe đang bị khóa khẩn cấp."}

        # --- BƯỚC 2: PHÂN LƯỒNG XỬ LÝ THEO CỔNG ---
        if gate_type == "VAO":
            try:
                log_in_response = await client.post(
                    f"{DB_API_BASE_URL}/log-in", 
                    json={"qr_code": qr_code, "bien_so": bien_so},
                    timeout=5.0
                )
                if log_in_response.status_code != 200:
                    try:
                        error_data = log_in_response.json()
                        # Bắt mã lỗi báo sai biển số từ DB
                        if error_data.get("error_code") == "MISMATCH_PLATE":
                            return {"status": "warning", "message": "Cảnh báo an ninh: Biển số không khớp / Nghi trộm!"}
                    except Exception:
                        pass
                    return {"status": "error", "message": "Lỗi ghi nhận xe vào trên DB."}
            except httpx.RequestError:
                return {"status": "error", "message": "Mất kết nối khi ghi log Xe Vào."}
            
            action_msg = "Ghi nhận xe VÀO thành công."

        elif gate_type == "RA":
            # Gọi hàm tính phí tự động
            muc_phi = tinh_phi_gui_xe()
            
            if float(xe_info.get("balance", 0)) < muc_phi:
                return {"status": "rejected", "message": f"Tài khoản không đủ {muc_phi}đ để ra cổng."}
            
            try:
                deduct_response = await client.post(
                    f"{DB_API_BASE_URL}/deduct", 
                    json={"qr_code": qr_code, "bien_so": bien_so, "amount": muc_phi},
                    timeout=5.0
                )
                if deduct_response.status_code != 200:
                    try:
                        error_data = deduct_response.json()
                        # Bắt mã lỗi báo sai biển số từ DB lúc ra cổng
                        if error_data.get("error_code") == "MISMATCH_PLATE":
                            return {"status": "warning", "message": "Cảnh báo an ninh: Biển số không khớp / Nghi trộm!"}
                    except Exception:
                        pass
                    return {"status": "error", "message": "Lỗi trừ tiền, hủy lệnh mở cổng."}
            except httpx.RequestError:
                return {"status": "error", "message": "Mất kết nối khi gọi API trừ tiền."}
            
            action_msg = f"Đã trừ {muc_phi}đ và ghi nhận xe RA thành công."
        
        else:
            return {"status": "error", "message": "Tham số gate_type không hợp lệ (Chỉ nhận 'VAO' hoặc 'RA')."}

        # --- BƯỚC 3: MỞ BARIE ---
        if arduino and arduino.is_open:
            try:
                arduino.write(b'1')
                # Tự động gửi lệnh đóng Barie sau 3 giây để tránh lỗi phần cứng
                asyncio.create_task(close_barie_after_delay(3))
            except serial.SerialException:
                return {"status": "error", "message": "Lỗi phần cứng khi mở Barie."}
            
        return {"status": "success", "message": action_msg}

# Hàm phụ trợ đóng Barie (Chạy ngầm không làm chậm thời gian phản hồi)
async def close_barie_after_delay(delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    if arduino and arduino.is_open:
        try:
            arduino.write(b'0')
        except serial.SerialException:
            print("Lỗi hệ thống: Không thể gửi lệnh đóng Barie")

# ==========================================
# 3. ENDPOINT ĐÓN DỮ LIỆU TỪ CAMERA
# ==========================================
@app.post("/webhook/camera-scan")
async def receive_camera_data(data: CameraData):
    return await hamanlinkcmtrequest(data.qr_code, data.gate_type, data.bien_so)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)