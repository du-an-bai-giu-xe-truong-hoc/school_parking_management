"""
Core configuration for the School Parking Management System
Cấu hình hệ thống cho ứng dụng quản lý bãi đỗ xe
"""

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

#Tải các biến môi trường từ file .env
load_dotenv()

class Settings(BaseSettings):
    """ứng dụng cấu hình cho hệ thống quản lý bãi đỗ xe"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # API settings
    db_api_base_url: str = os.getenv("DB_API_BASE_URL", "http://127.0.0.1:5000/api")

    # Hardware settings
    arduino_port: str = os.getenv("ARDUINO_PORT", "COM3")
    baud_rate: int = int(os.getenv("BAUD_RATE", "9600"))
    esp32_ip: str = os.getenv("ESP32_IP", "192.168.101.8")
    esp32_capture_url: str = os.getenv("ESP32_CAPTURE_URL", "http://192.168.101.8/capture")
    esp32_capture_timeout_seconds: int = int(os.getenv("ESP32_CAPTURE_TIMEOUT_SECONDS", "4"))
    parking_capture_dir: str = os.getenv("PARKING_CAPTURE_DIR", "app/storage/captures")

    # Application settings
    app_name: str = "School Parking Management System"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Security settings
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

# Global settings instance
settings = Settings()