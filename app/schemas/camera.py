"""Schemas cho dữ liệu camera gửi về khi phát hiện xe vào/ra"""

from pydantic import BaseModel

class CameraData(BaseModel):
    """Dữ liệu gửi từ camera khi phát hiện xe vào/ra"""
    qr_code: str
    bien_so: str = ""  # license plate detected by camera
    gate_type: str     # "VAO" or "RA"