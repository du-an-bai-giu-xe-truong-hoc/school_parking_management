import requests
import time
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from lunardate import LunarDate # Thư viện xử lý ngày âm lịch

app = FastAPI()

# ================= CÁC THÔNG SỐ HỆ THỐNG =================
DB_API_URL = "http://api-cua-minh-viet.com" 
ESP32_IP = "192.168.1.100"                  

SOLAR_HOLIDAYS = [
    "01/01", "09/01", "03/02", "14/02", "27/02", "08/03", "26/03", "21/04", 
    "22/04", "30/04", "01/05", "07/05", "15/05", "19/05", "01/06", "05/06", 
    "21/06", "28/06", "27/07", "19/08", "01/09", "02/09", "03/09", "10/10", 
    "13/10", "20/10", "31/10", "20/11", "22/12", "24/12", "25/12"
]
LUNAR_HOLIDAYS = [
    "01/01", "15/01", "03/03", "10/03", "15/04", "05/05", "15/07", "15/08", 
    "15/10", "23/12"
]
# =========================================================

# Hàng đợi lưu trữ thông báo để Client UI kéo về hiển thị
event_queue = []

class QRData(BaseModel):
    qr_code: str

def hamanlinkcmtrequest():
    # Hàm này được giữ nguyên hoàn toàn theo yêu cầu bảo trì của bạn
    pass

def add_ui_event(title: str, message: str):
    """Thêm thông báo vào hàng đợi"""
    event_queue.append({"title": title, "message": message})

def auto_close_gate():
    time.sleep(3)
    try:
        requests.get(f"http://{ESP32_IP}/control?cmd=close", timeout=5)
        print("[HỆ THỐNG] Đã đóng barie thành công!")
    except Exception as e:
        print(f"[LỖI] Không thể đóng cổng: {e}")

def calculate_fee(now: datetime) -> int:
    """Hàm tính toán giá vé dựa trên thời gian thực"""
    solar_str = now.strftime("%d/%m")
    if solar_str in SOLAR_HOLIDAYS:
        return 2000
        
    lunar_now = LunarDate.fromSolarDate(now.year, now.month, now.day)
    lunar_str = f"{lunar_now.day:02d}/{lunar_now.month:02d}"
    if lunar_str in LUNAR_HOLIDAYS:
        return 2000
        
    if now.weekday() == 6:
        return 2000
        
    if 5 <= now.hour < 17:
        return 1000
    else:
        return 2000

# ================= API ENDPOINTS =================

@app.post("/process-qr")
@app.post("/process-qr")
async def process_qr(data: QRData, background_tasks: BackgroundTasks):
    qr = data.qr_code
    now = datetime.now()
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S") 
    
    print(f"\n--- THỜI GIAN HIỆN TẠI: {current_time_str} | MÃ: {qr} ---")
    
    try:
        # -----------------------------------------------------------------
        # PHẦN GIẢ LẬP ĐỂ TEST (Thay thế cho việc gọi API thật bị lỗi)
        # -----------------------------------------------------------------
        # Giả sử mọi xe quét vào đều được hệ thống nhận diện là đang ở NGOÀI (để cho vào)
        # Nếu bạn muốn test trường hợp xe RA, hãy đổi "OUTSIDE" thành "INSIDE"
        car_data = {
            "status": "OUTSIDE", 
            "balance": 5000  # Giả sử ví có 5000đ
        }
        status = car_data.get('status')
        # -----------------------------------------------------------------

        if status == "OUTSIDE":
            print("-> Hệ thống nhận diện: XE ĐANG VÀO")
            # (Phần này tạm thời bỏ qua gọi DB thật để tránh lỗi kết nối)
            # requests.post(f"{DB_API_URL}/log-entry", json={"qr_code": qr, "entry_time": current_time_str})
            
            try:
                requests.get(f"http://{ESP32_IP}/control?cmd=open", timeout=2)
            except:
                print("[ESP32] Không tìm thấy mạch, bỏ qua điều khiển Barie.")
                
            add_ui_event("Xe Vào", f"Ghi nhận xe {qr} VÀO lúc:\n{current_time_str}")
            background_tasks.add_task(auto_close_gate)
            
            return {"status": "success", "action": "entry", "time": current_time_str}
            
        elif status == "INSIDE":
            print("-> Hệ thống nhận diện: XE ĐANG RA")
            fee = calculate_fee(now)
            current_balance = car_data.get('balance', 0)
            
            if current_balance >= fee:
                # new_balance = current_balance - fee
                try:
                    requests.get(f"http://{ESP32_IP}/control?cmd=open", timeout=2)
                except:
                    pass
                    
                msg = f"Xe {qr} RA BÃI thành công.\nPhí đỗ: {fee} VNĐ.\nSố dư ví: {current_balance - fee} VNĐ."
                add_ui_event("Xe Ra", msg)
                background_tasks.add_task(auto_close_gate)
                
                return {"status": "success", "action": "exit", "fee": fee, "time": current_time_str}
            else:
                add_ui_event("Từ chối", "Số dư ví không đủ để thanh toán!")
                return {"status": "denied", "reason": "Insufficient balance"}
                
    except Exception as e:
        print(f"[LỖI HỆ THỐNG]: {e}")
        return {"status": "error"}

@app.get("/api/ui-events")
async def get_ui_events():
    """Client UI sẽ liên tục gọi API này để lấy thông báo mới nhất"""
    global event_queue
    if not event_queue:
        return {"events": []}
    
    # Lấy toàn bộ sự kiện hiện có và làm trống hàng đợi
    current_events = event_queue.copy()
    event_queue.clear()
    return {"events": current_events}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
