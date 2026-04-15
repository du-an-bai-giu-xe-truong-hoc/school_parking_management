"""
Fee Service (Demo Version with Mock Logic)
"""

class FeeService:
    def calculate_fee(self, vehicle_type: str, duration_hours: float) -> int:
        """
        Mock logic for calculating parking fee
        """
        base_rate = {
            "xe_may": 5000,
            "o_to": 20000,
            "xe_dap": 2000
        }
        
        rate = base_rate.get(vehicle_type, 5000)
        return int(rate * max(1, duration_hours))

fee_service = FeeService()
