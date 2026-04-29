from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

class CameraData(BaseModel):
    qr_code: str
    gate_type: str
    bien_so: Optional[str] = None

class UserBase(BaseModel):
    full_name: str
    role: str
    identity_card: str
    phone_number: Optional[str] = None
    balance: float = 50000.0

class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    identity_card: Optional[str] = None
    phone_number: Optional[str] = None
    balance: Optional[float] = None

class VehicleBase(BaseModel):
    license_plate: str
    vehicle_type: str
    owner_id: int
    color: Optional[str] = None
    is_locked: bool = False
    lock_reason: Optional[str] = None

class VehicleResponse(VehicleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class VehicleScanRequest(BaseModel):
    qr_code: str
    bien_so: str
    lane: Optional[str] = None
    local_image_base64: Optional[str] = None


class ParkingEntryRequest(VehicleScanRequest):
    pass


class ParkingExitRequest(VehicleScanRequest):
    pass


class ParkingPreviewRequest(BaseModel):
    qr_code: str
    bien_so: Optional[str] = None

class EmergencyOpenRequest(BaseModel):
    lane: str
    gate_type: str


class ParkingPreviewResponse(BaseModel):
    status: str
    message: str
    vehicle_id: Optional[int] = None
    db_license_plate: Optional[str] = None
    owner_name: Optional[str] = None
    owner_identity_card: Optional[str] = None
    owner_balance: Optional[float] = None
    vehicle_locked: Optional[bool] = None
    lock_reason: Optional[str] = None
    time_in: Optional[datetime] = None


class ParkingScanResponse(BaseModel):
    status: str
    action: str
    message: str
    decision: str
    similarity_score: float
    threshold: float
    transaction_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    db_license_plate: Optional[str] = None
    scanned_plate: Optional[str] = None
    time_in: Optional[datetime] = None
    time_out: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    fee: Optional[float] = None
    string_similarity_score: Optional[float] = None
    image_similarity_score: Optional[float] = None
    owner_name: Optional[str] = None
    owner_identity_card: Optional[str] = None
    owner_balance: Optional[float] = None
    vehicle_locked: Optional[bool] = None
    lock_reason: Optional[str] = None
    alert_security: bool = False
    insufficient_balance: bool = False
    gate_open_seconds: int = 0
    entry_iot_image_path: Optional[str] = None
    exit_iot_image_path: Optional[str] = None
    entry_local_image_path: Optional[str] = None
    exit_local_image_path: Optional[str] = None
    barcode_payload: Dict[str, Any] = Field(default_factory=dict)


class TransactionHistoryItem(BaseModel):
    transaction_id: int
    vehicle_id: int
    license_plate: str
    owner_name: str
    identity_card: str
    owner_balance: float
    vehicle_type: str
    time_in: datetime
    time_out: Optional[datetime] = None
    status: str
    fee: float
    lane: Optional[str] = None
    image_similarity_score: float = 0.0
    alert_flag: bool = False


class TransactionResponse(BaseModel):
    id: int
    vehicle_id: int
    time_in: datetime
    time_out: Optional[datetime] = None
    status: str
    fee: float
    lane: Optional[str] = None
    barcode_raw: Optional[str] = None
    scanned_plate: Optional[str] = None
    entry_iot_image_path: Optional[str] = None
    exit_iot_image_path: Optional[str] = None
    entry_local_image_path: Optional[str] = None
    exit_local_image_path: Optional[str] = None
    image_similarity_score: float = 0.0
    alert_flag: bool = False

    model_config = ConfigDict(from_attributes=True)