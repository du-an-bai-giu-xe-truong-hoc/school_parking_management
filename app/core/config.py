"""
Core configuration for the School Parking Management System
Cấu hình hệ thống cho ứng dụng quản lý bãi đỗ xe
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

#Tải các biến môi trường từ file .env
load_dotenv()

class Settings(BaseSettings):
    """ứng dụng cấu hình cho hệ thống quản lý bãi đỗ xe"""

    # API settings
    db_api_base_url: str = os.getenv("DB_API_BASE_URL", "http://127.0.0.1:5000/api")

    # Hardware settings
    arduino_port: str = os.getenv("ARDUINO_PORT", "COM3")
    baud_rate: int = int(os.getenv("BAUD_RATE", "9600"))
    esp32_ip: str = os.getenv("ESP32_IP", "192.168.1.100")

    # Application settings
    app_name: str = "School Parking Management System"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Security settings
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()