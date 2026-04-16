# gui/utils/api_client.py
import requests
import logging
from dotenv import load_dotenv
import os
from datetime import datetime
load_dotenv()
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")
class ApiClient:
    @staticmethod
    def _request(method: str, endpoint: str, **kwargs):
        url = f"{BASE_URL}{endpoint}"
        try:
            resp = requests.request(method, url, timeout=8, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            logging.error(f"❌ Không kết nối được backend {url}")
            return {"error": "Không kết nối được backend. Kiểm tra FastAPI đang chạy port 8000 chưa?"}
        except requests.exceptions.HTTPError as e:
            logging.error(f"❌ API Error {url}: {e.response.status_code} - {e.response.text}")
            return {"error": f"API lỗi {e.response.status_code}"}
        except Exception as e:
            logging.error(f"❌ Unexpected error {url}: {e}")
            return {"error": str(e)}
    @staticmethod
    def get(endpoint: str, params=None):
        return ApiClient._request("GET", endpoint, params=params)
    @staticmethod
    def post(endpoint: str, json_data: dict):
        return ApiClient._request("POST", endpoint, json=json_data)
    # Các endpoint quan trọng (dựa trên repo của bạn)
    @staticmethod
    def get_dashboard():
        return ApiClient.get("/stats/dashboard")
    @staticmethod
    def check_vehicle(plate: str, lane: str = "A"):
        return ApiClient.post("/vehicles/check", {"plate": plate, "lane": lane})
    @staticmethod
    def open_barrier(lane: str):
        # Chỉ gọi khi đã check đủ điều kiện (được gọi từ page)
        return ApiClient.post("/barrier/open", {"lane": lane})
    @staticmethod
    def get_transaction_history(plate: str = None, limit=20):
        params = {"plate": plate, "limit": limit} if plate else {"limit": limit}
        return ApiClient.get("/transactions/history", params=params)
    @staticmethod
    def update_balance(vehicle_id: int, amount: int, action: str):
        return ApiClient.post("/transactions/balance", {
            "vehicle_id": vehicle_id,
            "amount": amount,
            "action": action # "add" hoặc "subtract"
        })
