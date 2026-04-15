# ==========================================
# FILE: app/services/fee_service.py
# MỤC ĐÍCH: Xử lý logic tính tiền gửi xe (Mock cho nhánh AI)
# ==========================================

def calculate_parking_fee(vehicle_type: str) -> float:
    """Hàm giả lập tính phí để không cản trở nhánh AI hoạt động"""
    if vehicle_type == "Bicycle":
        return 1000.0
    elif vehicle_type == "Motorbike":
        return 3000.0
    return 10000.0

def calculate_duration_fee(time_in, time_out) -> float:
    """Hàm giả lập tính phụ phí thời gian"""
    return 0.0