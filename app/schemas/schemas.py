from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ==========================================
# BIỂU MẪU CAMERA (Đón dữ liệu từ AI Module)
# ==========================================
class CameraData(BaseModel):
    qr_code: str
    gate_type: str  # "VAO" hoặc "RA"
    bien_so: Optional[str] = None

# ==========================================
# BIỂU MẪU NGƯỜI DÙNG (Users)
# ==========================================
class UserBase(BaseModel):
    full_name: str
    role: str
    identity_card: str
    phone_number: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True # Cho phép Pydantic đọc dữ liệu từ SQLAlchemy

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    identity_card: Optional[str] = None
    phone_number: Optional[str] = None

# ==========================================
# BIỂU MẪU PHƯƠNG TIỆN (Vehicles)
# ==========================================
class VehicleBase(BaseModel):
    license_plate: str
    vehicle_type: str
    owner_id: int
    color: Optional[str] = None

class VehicleResponse(VehicleBase):
    id: int

    class Config:
        from_attributes = True