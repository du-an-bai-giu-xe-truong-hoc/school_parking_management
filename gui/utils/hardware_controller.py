# gui/utils/hardware_controller.py - Reuse pyserial từ repo
import serial
import logging
import time
class HardwareController:
    def __init__(self):
        self.port = None
        try:
            # Đọc từ .env hoặc config của repo
            self.port = serial.Serial('/dev/ttyUSB0', 9600, timeout=1) # thay đổi port nếu cần
            logging.info("✅ Kết nối barrier thành công")
        except Exception as e:
            logging.warning(f"⚠️ Không kết nối được barrier: {e} (chế độ simulate)")
    def open_barrier(self, lane: str = "A"):
        if self.port:
            self.port.write(b'OPEN\n') # lệnh thực tế theo hardware repo
            time.sleep(0.5)
            logging.info(f"🚧 Mở barrier làn {lane}")
            return True
        else:
            logging.info(f"🔧 SIMULATE: Mở barrier làn {lane}")
            return True # simulate cho test
