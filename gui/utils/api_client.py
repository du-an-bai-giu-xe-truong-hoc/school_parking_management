import logging
import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("FASTAPI_URL", "http://localhost:8000").rstrip("/")
API_PREFIX = os.getenv("FASTAPI_PREFIX", "/api")
REQUEST_TIMEOUT = float(os.getenv("API_TIMEOUT_SECONDS", "8"))

class ApiClient:
    """Thin HTTP client for the FastAPI backend."""

    @staticmethod
    def _url(path: str) -> str:
        clean_path = path if path.startswith("/") else f"/{path}"
        prefix = API_PREFIX if API_PREFIX.startswith("/") else f"/{API_PREFIX}"
        if clean_path == prefix or clean_path.startswith(f"{prefix}/"):
            return f"{BASE_URL}{clean_path}"
        return f"{BASE_URL}{prefix}{clean_path}"

    @staticmethod
    def _request(method: str, path: str, **kwargs) -> Optional[Any]:
        try:
            response = requests.request(
                method=method,
                url=ApiClient._url(path),
                timeout=REQUEST_TIMEOUT,
                **kwargs,
            )
            response.raise_for_status()
            if not response.content:
                return {}
            return response.json()
        except Exception as exc:
            logging.error("API %s %s failed: %s", method, path, exc)
            return None

    @staticmethod
    def get_vehicle_by_plate(plate: str) -> Optional[Dict[str, Any]]:
        return ApiClient._request("GET", f"/vehicles/by-plate/{plate}")

    @staticmethod
    def preview_vehicle(qr_code: str, bien_so: str = "") -> Optional[Dict[str, Any]]:
        payload = {"qr_code": qr_code, "bien_so": bien_so or None}
        return ApiClient._request("POST", "/parking/preview", json=payload)

    @staticmethod
    def process_entry(
        qr_code: str,
        bien_so: str,
        lane: str = "",
        local_image_base64: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "qr_code": qr_code,
            "bien_so": bien_so,
            "lane": lane or None,
            "local_image_base64": local_image_base64,
        }
        return ApiClient._request("POST", "/parking/entry", json=payload)

    @staticmethod
    def process_exit(
        qr_code: str,
        bien_so: str,
        lane: str = "",
        local_image_base64: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "qr_code": qr_code,
            "bien_so": bien_so,
            "lane": lane or None,
            "local_image_base64": local_image_base64,
        }
        return ApiClient._request("POST", "/parking/exit", json=payload)

    @staticmethod
    def get_parking_history(limit: int = 200) -> Optional[Any]:
        return ApiClient._request("GET", f"/parking/history?limit={limit}")

    @staticmethod
    def get_active_transactions(limit: int = 200) -> Optional[Any]:
        return ApiClient._request("GET", f"/parking/active?limit={limit}")

    @staticmethod
    def get_transactions(limit: int = 200) -> Optional[Any]:
        return ApiClient._request("GET", f"/transactions/?limit={limit}")

    @staticmethod
    def create_transaction(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        gate_type = str(data.get("gate_type", "")).upper()
        if gate_type == "VAO":
            return ApiClient.process_entry(
                qr_code=str(data.get("qr_code", "")),
                bien_so=str(data.get("bien_so", "")),
                lane=str(data.get("lane", "")),
                local_image_base64=data.get("local_image_base64"),
            )
        if gate_type == "RA":
            return ApiClient.process_exit(
                qr_code=str(data.get("qr_code", "")),
                bien_so=str(data.get("bien_so", "")),
                lane=str(data.get("lane", "")),
                local_image_base64=data.get("local_image_base64"),
            )
        return None
