import math


def calculate_parking_fee(vehicle_type: str) -> float:
    """Base fee by vehicle type."""
    if vehicle_type == "Bicycle":
        return 1000.0
    if vehicle_type == "Motorbike":
        return 3000.0
    return 10000.0


def calculate_duration_fee(time_in, time_out) -> float:
    """Simple surcharge after 2 hours parking time."""
    if time_in is None or time_out is None:
        return 0.0

    total_minutes = max((time_out - time_in).total_seconds(), 0) / 60.0
    if total_minutes <= 120:
        return 0.0

    overtime_hours = math.ceil((total_minutes - 120) / 60.0)
    return float(overtime_hours * 1000)