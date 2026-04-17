"""
API routes for the parking management system
Hệ thống quản lý bãi đỗ xe - Chế độ kết nối Database thực
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Import hạ tầng kỹ thuật
from app.db.session import get_db
from app.models.models import User, Vehicle, Transaction
from app.schemas.schemas import CameraData, UserResponse, UserUpdate, VehicleResponse # Đảm bảo đã định nghĩa các schema này
from app.services.parking_service import parking_service
from app.api.camera import router as camera_router

router = APIRouter()

# Tích hợp module xử lý Camera
router.include_router(camera_router, prefix="/camera", tags=["camera"])

# ==========================================
# CAMERA ENDPOINTS - Xử lý dữ liệu thời gian thực
# ==========================================

@router.post("/webhook/camera-scan")
async def receive_camera_data(data: CameraData, db: Session = Depends(get_db)):
    """
    Tiếp nhận dữ liệu từ Camera AI và đối soát trực tiếp với Database
    """
    # Lưu ý: Truyền thêm 'db' vào service để nó có thể truy vấn bảng
    return await parking_service.process_vehicle_request(
        db=db,
        qr_code=data.qr_code,
        gate_type=data.gate_type,
        bien_so=data.bien_so
    )

# ==========================================
# USER MANAGEMENT - Quản lý hồ sơ chủ xe
# ==========================================

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Truy xuất thông tin người dùng từ SQL Server"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ người dùng.")
    return user

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Cập nhật thông tin hồ sơ người dùng"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Đối tượng không tồn tại.")
    
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

# ==========================================
# VEHICLE MANAGEMENT - Quản lý phương tiện
# ==========================================

@router.get("/vehicles/", response_model=List[VehicleResponse])
async def get_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Truy xuất danh sách phương tiện thực tế từ SQL Server"""
    try:
        # Valkyrie Yêu cầu: Bổ sung lệnh xếp hàng order_by(Vehicle.id)
        vehicles = db.query(Vehicle).order_by(Vehicle.id).offset(skip).limit(limit).all()
        return vehicles
    except Exception as e:
        print(f"[LỖI TRUY VẤN]: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi truy xuất cơ sở dữ liệu.")
@router.post("/vehicles/", response_model=VehicleResponse)
async def create_vehicle(vehicle_data: dict, db: Session = Depends(get_db)):
    """Đăng ký phương tiện mới vào hệ thống"""
    new_vehicle = Vehicle(**vehicle_data)
    db.add(new_vehicle)
    try:
        db.commit()
        db.refresh(new_vehicle)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Lỗi đăng ký phương tiện: {str(e)}")
    return new_vehicle

# ==========================================
# TRANSACTION - Lịch sử bãi xe
# ==========================================

@router.get("/transactions/")
async def get_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Truy xuất toàn bộ lịch sử ra vào bãi xe"""
    transactions = db.query(Transaction).offset(skip).limit(limit).all()
    return transactions

# ==========================================
# HEALTH CHECK
# ==========================================

@router.get("/health")
async def health_check():
    """Kiểm tra tình trạng máy chủ"""
    return {"status": "healthy", "service": "parking-api-production"}