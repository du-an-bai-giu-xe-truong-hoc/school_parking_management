# gui/utils/hardware_controller.py
"""
Hardware Controller cho hệ thống quản lý bãi xe
Hỗ trợ: ESP32 + SG90 + RFID-RC522 + IR Sensor
Tác giả: Senior Python GUI Architect
"""

import time
import threading
import logging
from typing import Optional, Dict, Any
import serial
import requests
import serial.tools.list_ports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HardwareController:
    def __init__(self):
        self.ser: Optional[serial.Serial] = None
        self.connected = False
        self.use_http = False
        self.http_base_url = ""          # Ví dụ: http://192.168.1.184
        self.mock_mode = False           # Bật khi test không có hardware
        self.lock = threading.Lock()     # Tránh race condition

    def connect(self, port: str = None, baudrate: int = 115200, http_url: str = None) -> bool:
        """
        Kết nối phần cứng
        - port: COM3 (Windows) hoặc /dev/ttyUSB0 (Linux)
        - http_url: nếu ESP32 chạy web server (khuyến nghị)
        """
        with self.lock:
            if http_url:
                self.use_http = True
                self.http_base_url = http_url.rstrip('/')
                self.mock_mode = False
                logger.info(f"🔗 Kết nối HTTP ESP32: {self.http_base_url}")
                self.connected = True
                return True

            # Thử kết nối Serial
            if not port:
                # Tự động tìm cổng ESP32
                ports = [p.device for p in serial.tools.list_ports.comports() 
                        if "USB" in p.description or "CP210" in p.description or "CH340" in p.description]
                port = ports[0] if ports else None

            if port:
                try:
                    self.ser = serial.Serial(port, baudrate, timeout=1)
                    self.connected = True
                    self.mock_mode = False
                    logger.info(f"✅ Kết nối Serial thành công: {port}")
                    return True
                except Exception as e:
                    logger.error(f"❌ Không kết nối được Serial {port}: {e}")

            # Fallback sang Mock mode (test)
            self.mock_mode = True
            self.connected = True
            logger.warning("⚠️ Đang chạy ở MOCK MODE (không có hardware thật)")
            return True

    def _send_command(self, command: str) -> bool:
        """Gửi lệnh qua Serial hoặc HTTP"""
        if self.mock_mode:
            logger.info(f"[MOCK] Gửi lệnh: {command}")
            time.sleep(0.3)  # Giả lập thời gian thực tế
            return True

        if self.use_http:
            try:
                resp = requests.get(f"{self.http_base_url}/{command}", timeout=3)
                return resp.status_code == 200
            except Exception as e:
                logger.error(f"HTTP error: {e}")
                return False

        # Serial mode
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{command}\n".encode())
                time.sleep(0.2)
                return True
            except Exception as e:
                logger.error(f"Serial write error: {e}")
                return False
        return False

    def open_barrier(self, lane: str = "A") -> bool:
        """Mở barrier (SG90)"""
        cmd = f"OPEN_{lane}"
        success = self._send_command(cmd)
        if success:
            logger.info(f"🚪 Barrier {lane} đã MỞ")
        return success

    def close_barrier(self, lane: str = "A") -> bool:
        """Đóng barrier (SG90)"""
        cmd = f"CLOSE_{lane}"
        success = self._send_command(cmd)
        if success:
            logger.info(f"🚪 Barrier {lane} đã ĐÓNG")
        return success

    def read_rfid(self) -> Optional[str]:
        """Đọc thẻ RFID-RC522"""
        if self.mock_mode:
            # Mock vài mã thẻ để test
            mock_cards = ["A1B2C3D4", "E5F6G7H8", None]
            return mock_cards[int(time.time()) % 3]

        if self.use_http:
            try:
                resp = requests.get(f"{self.http_base_url}/read_rfid", timeout=2)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("rfid")
            except:
                pass
            return None

        # Serial
        if self.ser:
            try:
                self.ser.write(b"READ_RFID\n")
                time.sleep(0.3)
                if self.ser.in_waiting:
                    line = self.ser.readline().decode().strip()
                    if line.startswith("RFID:"):
                        return line.split(":")[1].strip()
            except:
                pass
        return None

    def is_vehicle_present(self) -> bool:
        """Đọc IR Sensor: True = có xe"""
        if self.mock_mode:
            return True  # Giả lập luôn có xe khi test

        if self.use_http:
            try:
                resp = requests.get(f"{self.http_base_url}/ir_status", timeout=1)
                if resp.status_code == 200:
                    return resp.json().get("present", False)
            except:
                pass
            return False

        # Serial
        if self.ser:
            try:
                self.ser.write(b"READ_IR\n")
                time.sleep(0.1)
                if self.ser.in_waiting:
                    line = self.ser.readline().decode().strip()
                    return line == "IR:DETECTED"
            except:
                pass
        return False

    def disconnect(self):
        """Ngắt kết nối"""
        with self.lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.connected = False
            logger.info("🔌 Đã ngắt kết nối hardware")

# ==================== HƯỚNG DẪN SỬ DỤNG ====================

# Ví dụ sử dụng trong __init__ của XeVaoPage / XeRaPage:
# self.hardware = HardwareController()
# self.hardware.connect(http_url="http://192.168.1.184")   # Khuyến nghị dùng HTTP
# # Hoặc serial:
# self.hardware.connect(port="COM5")   # Windows
# # self.hardware.connect(port="/dev/ttyUSB0")  # Linux
