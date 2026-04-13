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

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin người dùng theo ID"""
    # TODO: Thêm logic lấy thông tin người dùng từ database
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Cập nhật thông tin người dùng"""
    # TODO: Thêm logic cập nhật thông tin người dùng
    raise HTTPException(status_code=501, detail="Not implemented yet")

# ==========================================
# VEHICLE MANAGEMENT ENDPOINTS
# ==========================================

@router.get("/vehicles/", response_model=List[VehicleResponse])
async def get_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Lấy danh sách phương tiện đã đăng ký"""
    # TODO: Thêm logic lấy danh sách phương tiện
    return []

@router.post("/vehicles/", response_model=VehicleResponse)
async def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    """Tạo phương tiện mới"""
    # TODO: Thêm logic tạo phương tiện mới
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """Lấy phương tiện theo ID"""
    # TODO: Thêm logic lấy phương tiện theo ID
    raise HTTPException(status_code=501, detail="Not implemented yet")

# ==========================================
# TRANSACTION ENDPOINTS
# ==========================================

@router.get("/transactions/", response_model=List[TransactionResponse])
async def get_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Lấy tất cả các giao dịch"""
    # TODO: Thêm logic lấy thông tin giao dịch
    return []

@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Lấy giao dịch theo ID"""
    # TODO: Thêm logic lấy giao dịch theo ID
    raise HTTPException(status_code=501, detail="Not implemented yet")

# ==========================================
# HEALTH CHECK ENDPOINTS
# ==========================================

@router.get("/health")
async def health_check():
    """System health check"""
    return {"status": "healthy", "service": "parking-api"}