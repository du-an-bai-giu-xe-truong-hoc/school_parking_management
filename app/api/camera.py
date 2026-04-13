from fastapi import APIRouter, UploadFile, File
from app.services.ocr_service import get_license_plate_text  # Import OCR function
import tempfile
import os

router = APIRouter()

@router.post("/detect-plate")
async def detect_plate(file: UploadFile = File(...)):
    """
    Phát hiện biển số xe từ ảnh upload
    """
    try:
        # Đọc nội dung file ảnh
        content = await file.read()

        # Gọi hàm OCR để nhận diện biển số xe
        plate_text = await get_license_plate_text(content)

        if not plate_text:
            return {"success": False, "message": "Không nhận diện được biển số xe"}

        return {"success": True, "plate": plate_text}

    except Exception as e:
        return {"success": False, "message": f"Lỗi xử lý: {str(e)}"}