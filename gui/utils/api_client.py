# gui/utils/api_client.py
import requests
import logging
from dotenv import load_dotenv
import os

load_dotenv()
BASE_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

class ApiClient:
    """Client gọi API FastAPI - reuse models/schemas đã có trong repo"""

    @staticmethod
    def get_vehicle_by_plate(plate: str):
        """Lấy thông tin xe theo biển số"""
        try:
            resp = requests.get(f"{BASE_URL}/vehicles/by-plate/{plate}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.error(f"API get_vehicle_by_plate lỗi: {e}")
            return None

    @staticmethod
    def check_balance(vehicle_id: int):
        try:
            resp = requests.get(f"{BASE_URL}/vehicles/{vehicle_id}/balance")
            resp.raise_for_status()
            return resp.json().get("balance", 0)
        except:
            return 0

    @staticmethod
    def create_transaction(data: dict):
        """Tạo giao dịch vào/ra"""
        try:
            resp = requests.post(f"{BASE_URL}/transactions/", json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.error(f"Create transaction lỗi: {e}")
            return None

    @staticmethod
    def open_barrier():
        """Gọi API mở barrier"""
        try:
            resp = requests.post(f"{BASE_URL}/hardware/open-barrier")
            return resp.status_code == 200
        except:
            return False
