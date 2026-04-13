"""
Pydantic schemas for data validation
Schemas Pydantic để validation dữ liệu
"""

from .camera import CameraData

__all__ = [
    "UserBase", "UserCreate", "UserUpdate", "UserResponse",
    "VehicleBase", "VehicleCreate", "VehicleUpdate", "VehicleResponse",
    "TransactionBase", "TransactionResponse",
    "CameraData"
]