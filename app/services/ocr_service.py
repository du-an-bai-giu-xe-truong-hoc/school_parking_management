"""
OCR Service using Google Cloud Vision API for license plate recognition
Service OCR sử dụng Google Cloud Vision để nhận diện biển số xe
"""

import os
from google.cloud import vision
import logging

logger = logging.getLogger(__name__)

# Set Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "app/core/mvbl-492911-81f79d8de732.json"

client = vision.ImageAnnotatorClient()

async def get_license_plate_text(image_content: bytes):
    """
    Extract license plate text from image using Google Cloud Vision
    Nhận diện biển số xe từ ảnh sử dụng Google Cloud Vision

    Args:
        image_content: Raw image bytes

    Returns:
        Extracted license plate text or None if not found
    """
    try:
        image = vision.Image(content=image_content)
        # Gợi ý tiếng Việt để nhận diện chính xác các ký tự đặc thù
        image_context = vision.ImageContext(language_hints=["vi"])

        # Gọi API nhận diện văn bản thưa (phù hợp cho biển số xe)
        response = client.text_detection(image=image, image_context=image_context)
        texts = response.text_annotations

        if not texts:
            return None

        # Làm sạch chuỗi: loại bỏ dấu xuống dòng do biển số 2 dòng gây ra
        return texts[0].description.replace("\n", " ").strip()

    except Exception as e:
        logger.error(f"Error in OCR processing: {str(e)}")
        return None