"""
API routes for the parking management system
Các route API cho hệ thống quản lý bãi đỗ xe
"""

from fastapi import APIRouter
from app.schemas import CameraData
from app.services.parking_service import parking_service
from app.api.camera import router as camera_router

router = APIRouter()

router.include_router(camera_router, prefix="/camera", tags=["camera"])

# ==========================================
# CAMERA ENDPOINTS - Đón dữ liệu từ Camera
# ==========================================

@router.post("/webhook/camera-scan")
async def receive_camera_data(data: CameraData):
    """
    Endpoint webhook nhận dữ liệu từ camera quét QR/biển số
    """
    return await parking_service.process_vehicle_request(
        qr_code=data.qr_code,
        gate_type=data.gate_type,
        bien_so=data.bien_so
    )

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    """Lấy thông tin người dùng theo ID (Demo mock)"""
    return {"user_id": user_id, "name": "Mock User", "role": "student"}

@router.put("/users/{user_id}")
async def update_user(user_id: int, user_update: dict):
    """Cập nhật thông tin người dùng (Demo mock)"""
    return {"user_id": user_id, "status": "updated", "data": user_update}

# ==========================================
# VEHICLE MANAGEMENT ENDPOINTS
# ==========================================

@router.get("/vehicles/")
async def get_vehicles(skip: int = 0, limit: int = 100):
    """Lấy danh sách phương tiện đã đăng ký (Demo mock)"""
    return [
        {"id": 1, "bien_so": "29A-12345", "owner": "Mock User"}
    ]

@router.post("/vehicles/")
async def create_vehicle(vehicle: dict):
    """Tạo phương tiện mới (Demo mock)"""
    return {"id": 2, "bien_so": vehicle.get("bien_so", "Unknown"), "status": "created"}

@router.get("/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: int):
    """Lấy phương tiện theo ID (Demo mock)"""
    return {"id": vehicle_id, "bien_so": "29A-12345", "owner": "Mock User"}

# ==========================================
# TRANSACTION ENDPOINTS
# ==========================================

@router.get("/transactions/")
async def get_transactions(skip: int = 0, limit: int = 100):
    """Lấy tất cả các giao dịch (Demo mock)"""
    return [
        {"id": 1, "bien_so": "29A-12345", "gate": "VAO", "time": "2026-04-15 08:00"}
    ]

@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: int):
    """Lấy giao dịch theo ID (Demo mock)"""
    return {"id": transaction_id, "bien_so": "29A-12345", "gate": "VAO"}

# ==========================================
# HEALTH CHECK ENDPOINTS
# ==========================================

@router.get("/health")
async def health_check():
    """System health check"""
    return {"status": "healthy", "service": "parking-api"}