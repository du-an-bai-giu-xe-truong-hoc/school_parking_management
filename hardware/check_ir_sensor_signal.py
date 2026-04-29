import argparse
import os
import time
from datetime import datetime
from typing import Optional

import requests

DEFAULT_BASE_URL = os.getenv("ESP32_BASE_URL", "http://192.168.81.61").rstrip("/")
DEFAULT_ENDPOINTS = ["/ir-status", "/sensor", "/status"]
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("IR_READ_TIMEOUT_SECONDS", "2"))
DEFAULT_POLL_SECONDS = float(os.getenv("IR_POLL_SECONDS", "0.3"))


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _parse_bool_value(value) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) == 1
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "on", "active", "detected"}
    return None


def _extract_ir_state(payload) -> Optional[bool]:
    if isinstance(payload, dict):
        nested = payload.get("status")
        if isinstance(nested, dict):
            nested_state = _extract_ir_state(nested)
            if nested_state is not None:
                return nested_state

        for key in ("car_present", "ir", "ir_state", "ir_sensor", "ir_detected", "triggered", "motion"):
            if key in payload:
                parsed = _parse_bool_value(payload.get(key))
                if parsed is not None:
                    return parsed

    if isinstance(payload, str):
        return _parse_bool_value(payload)

    return None


def read_ir_state(base_url: str, endpoints: list[str], timeout_seconds: float) -> Optional[bool]:
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=timeout_seconds)
            response.raise_for_status()

            content_type = (response.headers.get("Content-Type") or "").lower()
            if "application/json" in content_type:
                state = _extract_ir_state(response.json())
            else:
                state = _extract_ir_state(response.text)

            if state is not None:
                return state
        except requests.RequestException:
            continue
        except ValueError:
            continue

    return None


def monitor_ir(base_url: str, endpoints: list[str], timeout_seconds: float, poll_seconds: float) -> None:
    print(f"[{_timestamp()}] Dang theo doi IR sensor tai: {base_url}")
    print(f"[{_timestamp()}] Endpoint thu: {', '.join(endpoints)}")
    print(f"[{_timestamp()}] Nhan Ctrl+C de dung.\n")

    last_state: Optional[bool] = None
    while True:
        current_state = read_ir_state(base_url, endpoints, timeout_seconds)

        if current_state is None:
            print(f"[{_timestamp()}] Khong doc duoc trang thai IR tu cac endpoint.")
            time.sleep(poll_seconds)
            continue

        if last_state is None or current_state != last_state:
            if current_state:
                print(f"[{_timestamp()}] THONG BAO: IR sensor DA PHAT HIEN tin hieu (co xe).")
            else:
                print(f"[{_timestamp()}] THONG BAO: IR sensor KHONG phat hien tin hieu (khong co xe).")

        last_state = current_state
        time.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kiem tra ESP32 IR sensor va hien thi thong bao.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Dia chi base cua ESP32, vd: http://192.168.81.61")
    parser.add_argument(
        "--endpoints",
        default=",".join(DEFAULT_ENDPOINTS),
        help="Danh sach endpoint cach nhau boi dau phay, vd: /ir-status,/sensor,/status",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Timeout moi request (giay)")
    parser.add_argument("--poll", type=float, default=DEFAULT_POLL_SECONDS, help="Chu ky polling (giay)")
    parser.add_argument("--once", action="store_true", help="Chi kiem tra 1 lan roi thoat")

    args = parser.parse_args()

    endpoints = [item.strip() for item in args.endpoints.split(",") if item.strip()]
    if not endpoints:
        endpoints = DEFAULT_ENDPOINTS

    if args.once:
        state = read_ir_state(args.base_url.rstrip("/"), endpoints, args.timeout)
        if state is None:
            print(f"[{_timestamp()}] Khong doc duoc trang thai IR.")
            return
        if state:
            print(f"[{_timestamp()}] THONG BAO: IR sensor DA PHAT HIEN tin hieu (co xe).")
        else:
            print(f"[{_timestamp()}] THONG BAO: IR sensor KHONG phat hien tin hieu (khong co xe).")
        return

    try:
        monitor_ir(args.base_url.rstrip("/"), endpoints, args.timeout, args.poll)
    except KeyboardInterrupt:
        print(f"\n[{_timestamp()}] Da dung theo doi IR sensor.")


if __name__ == "__main__":
    main()
