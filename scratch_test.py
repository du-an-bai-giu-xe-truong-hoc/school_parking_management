from app.parking_log import log_parking_event
import time

print("Test 1: VÀO BÃI")
action, ts = log_parking_event("REFC-SV001", "59A-12345")
print(f"Result: {action} at {ts}")

time.sleep(1)

print("Test 2: RA BÃI")
action, ts = log_parking_event("REFC-SV001", "59A-12345")
print(f"Result: {action} at {ts}")
