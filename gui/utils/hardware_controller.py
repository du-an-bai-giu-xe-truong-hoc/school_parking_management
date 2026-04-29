# gui/utils/hardware_controller.py
import serial
import logging
from dotenv import load_dotenv
import os

load_dotenv()

class HardwareController:
    """Điều khiển barrier qua pyserial (reuse code trong folder hardware/ của repo)"""

    def __init__(self):
        self.port = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
        self.baudrate = int(os.getenv("BAUDRATE", 9600))
        self.mock_mode = os.getenv("DISABLE_HARDWARE", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.ser = None

    def connect(self) -> bool:
        if self.mock_mode:
            logging.info("[MOCK] Hardware mode disabled by DISABLE_HARDWARE=true")
            return True

        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            logging.info("✅ Kết nối barrier thành công")
            return True
        except Exception as e:
            logging.error(f"❌ Không kết nối được barrier: {e}")
            return False

    def open_barrier(self, lane: str = "A") -> bool:
        if self.mock_mode:
            logging.info(f"[MOCK] Open barrier lane {lane}")
            return True

        if not self.ser:
            if not self.connect():
                return False
        try:
            cmd = b'OPEN_A\n' if lane == "A" else b'OPEN_B\n'
            self.ser.write(cmd)
            logging.info(f"🚧 Mở barrier lane {lane}")
            return True
        except Exception as e:
            logging.error(f"Mở barrier lỗi: {e}")
            return False

    def close(self):
        if self.ser:
            self.ser.close()
