"""HTTP routes for parking workflow, CRUD, and monitoring."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.camera import router as camera_router
from app.db.session import get_db
from app.models.models import Transaction, User, Vehicle
from app.schemas.schemas import (
    CameraData,
    ParkingEntryRequest,
    ParkingExitRequest,
    ParkingPreviewRequest,
    ParkingPreviewResponse,
    ParkingScanResponse,
    TransactionHistoryItem,
    TransactionResponse,
    UserResponse,
    UserUpdate,
    VehicleBase,
    VehicleResponse,
)
from app.services.parking_service import parking_service

router = APIRouter()
router.include_router(camera_router, prefix="/camera", tags=["camera"])


@router.post("/webhook/camera-scan", response_model=ParkingScanResponse)
async def receive_camera_data(data: CameraData, db: Session = Depends(get_db)):
    return await parking_service.process_vehicle_request(
        db=db,
        qr_code=data.qr_code,
        gate_type=data.gate_type,
        bien_so=data.bien_so or "",
    )


@router.post("/parking/entry", response_model=ParkingScanResponse)
async def process_entry(data: ParkingEntryRequest, db: Session = Depends(get_db)):
    return await parking_service.process_entry(
        db=db,
        qr_code=data.qr_code,
        bien_so=data.bien_so,
        lane=data.lane,
        local_image_base64=data.local_image_base64,
    )


@router.post("/parking/exit", response_model=ParkingScanResponse)
async def process_exit(data: ParkingExitRequest, db: Session = Depends(get_db)):
    return await parking_service.process_exit(
        db=db,
        qr_code=data.qr_code,
        bien_so=data.bien_so,
        lane=data.lane,
        local_image_base64=data.local_image_base64,
    )


@router.post("/parking/preview", response_model=ParkingPreviewResponse)
async def preview_vehicle(data: ParkingPreviewRequest, db: Session = Depends(get_db)):
    return await parking_service.preview_vehicle(
        db=db,
        qr_code=data.qr_code,
        bien_so=data.bien_so or "",
    )
@router.post("/parking/emergency-open")
async def emergency_open(data: EmergencyOpenRequest):
    import logging
    logging.getLogger("api").warning(
        f"EMERGENCY OPEN: Lane {data.lane}, Gate {data.gate_type}"
    )
    return {"status": "success", "message": "Emergency open command received"}


@router.get("/parking/history", response_model=List[TransactionHistoryItem])
async def get_parking_history(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return parking_service.get_history(db=db, skip=skip, limit=limit)


@router.get("/parking/active")
async def get_active_parking(limit: int = 200, db: Session = Depends(get_db)):
    return parking_service.get_active_transactions(db=db, limit=limit)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Khong tim thay ho so nguoi dung.")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Doi tuong khong ton tai.")

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/vehicles/", response_model=List[VehicleResponse])
async def get_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return db.query(Vehicle).offset(skip).limit(limit).all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Loi truy xuat co so du lieu: {exc}") from exc


@router.get("/vehicles/by-plate/{plate}", response_model=VehicleResponse)
async def get_vehicle_by_plate(plate: str, db: Session = Depends(get_db)):
    normalized_target = "".join(ch for ch in plate.upper() if ch.isalnum())
    vehicles = db.query(Vehicle).all()
    for vehicle in vehicles:
        normalized_db_plate = "".join(ch for ch in vehicle.license_plate.upper() if ch.isalnum())
        if normalized_db_plate == normalized_target:
            return vehicle
    raise HTTPException(status_code=404, detail="Khong tim thay xe theo bien so.")


@router.post("/vehicles/", response_model=VehicleResponse)
async def create_vehicle(vehicle_data: VehicleBase, db: Session = Depends(get_db)):
    payload = vehicle_data.model_dump()
    new_vehicle = Vehicle(
        license_plate=payload["license_plate"],
        vehicle_type=payload["vehicle_type"],
        owner_id=payload["owner_id"],
        color=payload.get("color"),
        is_locked=bool(payload.get("is_locked", False)),
        lock_reason=payload.get("lock_reason"),
    )
    db.add(new_vehicle)
    try:
        db.commit()
        db.refresh(new_vehicle)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Loi dang ky phuong tien: {exc}") from exc
    return new_vehicle


@router.get("/transactions/", response_model=List[TransactionResponse])
async def get_transactions(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return (
        db.query(Transaction)
        .order_by(Transaction.time_in.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "school-parking-api"}