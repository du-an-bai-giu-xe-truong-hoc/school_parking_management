"""
Parking Service (Demo Version with Mock Logic)
"""

class ParkingService:
    async def process_vehicle_request(self, qr_code: str, gate_type: str, bien_so: str = ""):
        """
        Mock processing for camera webhook
        """
        print(f"[ParkingService] Received data - QR: {qr_code}, Gate: {gate_type}, License Plate: {bien_so}")
        
        # Simple mock logic
        if gate_type.upper() == "VAO":
            action = "OPEN_GATE_IN"
            message = f"Chào mừng xe {bien_so} vào bãi."
        elif gate_type.upper() == "RA":
            action = "OPEN_GATE_OUT"
            message = f"Tạm biệt xe {bien_so}. Đã trừ phí đỗ xe."
        else:
            action = "ERROR"
            message = "Loại cổng không hợp lệ"
            
        return {
            "status": "success",
            "action": action,
            "message": message,
            "data": {
                "qr_code": qr_code,
                "bien_so": bien_so,
                "gate_type": gate_type
            }
        }

# Global instance to be imported by routes
parking_service = ParkingService()
