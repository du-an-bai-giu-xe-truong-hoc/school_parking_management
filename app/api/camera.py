import os
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.services.ocr_service import get_license_plate_text

router = APIRouter()

_LATEST_FRAME_LOCK = threading.Lock()
_LATEST_FRAME_BYTES = b""
_LATEST_FRAME_MEDIA_TYPE = "image/jpeg"
_LATEST_FRAME_TS = 0.0
_AUTO_SYNC_THREAD: threading.Thread | None = None
_AUTO_SYNC_THREAD_LOCK = threading.Lock()
_AUTO_SYNC_LAST_OK_TS = 0.0
_AUTO_SYNC_LAST_ERROR = ""
_AUTO_SYNC_LAST_SOURCE = ""
_LAST_REMOTE_FRAME_SEQ = ""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _frame_storage_path() -> Path:
    default_path = _project_root() / "app" / "storage" / "captures" / "esp32_latest.jpg"
    configured = (os.getenv("ESP32_LATEST_FRAME_PATH") or "").strip()
    path = Path(configured) if configured else default_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _capture_archive_dir() -> Path:
    archive_dir = (os.getenv("ESP32_CAPTURE_ARCHIVE_DIR") or str(_project_root() / "capture")).strip()
    path = Path(archive_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _is_supported_image(content: bytes, media_type: str) -> bool:
    mt = (media_type or "").lower()
    if "image/" in mt:
        return True
    return content.startswith(b"\xff\xd8") or content.startswith(b"\x89PNG\r\n\x1a\n")


def _save_latest_frame(content: bytes, media_type: str, archive: bool = True) -> dict:
    global _LATEST_FRAME_BYTES, _LATEST_FRAME_MEDIA_TYPE, _LATEST_FRAME_TS

    if not _is_supported_image(content, media_type):
        raise HTTPException(status_code=400, detail="Du lieu upload khong phai anh hop le.")

    normalized_media_type = (media_type or "").split(";")[0].strip() or "image/jpeg"
    now = datetime.now()

    with _LATEST_FRAME_LOCK:
        _LATEST_FRAME_BYTES = bytes(content)
        _LATEST_FRAME_MEDIA_TYPE = normalized_media_type
        _LATEST_FRAME_TS = now.timestamp()

    storage = _frame_storage_path()
    storage.write_bytes(content)

    archive_path = None
    if archive:
        # Keep historical snapshots for hardware flow that reads from capture/.
        ext = ".png" if normalized_media_type == "image/png" else ".jpg"
        archive_name = f"cam_{now.strftime('%Y%m%d_%H%M%S_%f')}_{uuid4().hex}{ext}"
        archive_path = _capture_archive_dir() / archive_name
        archive_path.write_bytes(content)

    return {
        "ok": True,
        "message": "Da nhan frame tu ESP32-CAM.",
        "bytes": len(content),
        "media_type": normalized_media_type,
        "received_at": now.isoformat(),
        "saved_to": str(storage),
        "archived_to": str(archive_path) if archive_path is not None else None,
    }


def _load_latest_frame_from_disk() -> tuple[bytes, str] | None:
    storage = _frame_storage_path()
    if not storage.exists() or storage.stat().st_size == 0:
        return None

    content = storage.read_bytes()
    suffix = storage.suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"
    return content, media_type


def _get_cached_latest_frame() -> tuple[bytes, str, float] | None:
    with _LATEST_FRAME_LOCK:
        if _LATEST_FRAME_BYTES:
            return _LATEST_FRAME_BYTES, _LATEST_FRAME_MEDIA_TYPE, _LATEST_FRAME_TS

    on_disk = _load_latest_frame_from_disk()
    if on_disk is None:
        return None

    storage = _frame_storage_path()
    ts = storage.stat().st_mtime if storage.exists() else 0.0
    return on_disk[0], on_disk[1], ts


def _resolve_esp32_base_url() -> str:
    base = (os.getenv("ESP32_BASE_URL") or "").strip()
    if not base:
        ip = (os.getenv("ESP32_IP") or "192.168.81.61").strip()
        base = f"http://{ip}"
    if not base.startswith(("http://", "https://")):
        base = f"http://{base}"
    return base.rstrip("/")


def _build_esp32_capture_candidates() -> list[str]:
    configured_capture = (os.getenv("ESP32_CAPTURE_URL") or "").strip()
    if configured_capture:
        if not configured_capture.startswith(("http://", "https://")):
            configured_capture = f"http://{configured_capture}"

    base = _resolve_esp32_base_url()
    candidates: list[str] = []
    if configured_capture:
        candidates.append(configured_capture)

    parsed = urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else base
    # Prefer /latest so backend can refresh without generating extra capture side effects.
    for path in ("/latest", "/capture", "/cam-hi.jpg", "/"):
        candidates.append(f"{root}{path}")

    unique: list[str] = []
    seen = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return [item for item in unique if not _is_backend_loop_url(item)]


def _is_backend_loop_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        if not path.startswith("/api/camera/esp32"):
            return False

        backend = (os.getenv("FASTAPI_URL") or "http://localhost:8000").strip()
        if not backend.startswith(("http://", "https://")):
            backend = f"http://{backend}"
        backend_parsed = urlparse(backend)

        return parsed.netloc.lower() == backend_parsed.netloc.lower()
    except Exception:
        return False


def _fetch_esp32_image_bytes(timeout_seconds: float) -> tuple[bytes, str, str, str]:
    for url in _build_esp32_capture_candidates():
        try:
            resp = requests.get(url, timeout=timeout_seconds)
            resp.raise_for_status()
            content = resp.content or b""
            if not content:
                continue

            content_type = (resp.headers.get("Content-Type") or "").lower()
            is_image = "image" in content_type or content.startswith(b"\xff\xd8")
            if not is_image:
                continue

            media_type = content_type.split(";")[0].strip() if content_type else "image/jpeg"
            frame_seq = (resp.headers.get("X-Frame-Seq") or "").strip()
            return content, media_type or "image/jpeg", url, frame_seq
        except requests.RequestException:
            continue
    raise HTTPException(status_code=502, detail="Khong lay duoc anh tu ESP32-CAM qua WiFi.")


def _auto_sync_enabled() -> bool:
    return os.getenv("ESP32_AUTO_SYNC_ENABLED", "1").strip().lower() not in {"0", "false", "no"}


def _auto_sync_interval_seconds() -> float:
    raw = os.getenv("ESP32_AUTO_SYNC_SECONDS", "1.0").strip()
    try:
        return max(0.3, float(raw))
    except ValueError:
        return 1.0


def _auto_sync_latest_frame_once() -> bool:
    global _AUTO_SYNC_LAST_OK_TS, _AUTO_SYNC_LAST_ERROR, _AUTO_SYNC_LAST_SOURCE, _LAST_REMOTE_FRAME_SEQ
    timeout_seconds = float(os.getenv("ESP32_CAPTURE_TIMEOUT_SECONDS", "4"))
    image_bytes, media_type, source_url, remote_seq = _fetch_esp32_image_bytes(timeout_seconds=timeout_seconds)
    with _LATEST_FRAME_LOCK:
        unchanged = image_bytes == _LATEST_FRAME_BYTES and media_type == _LATEST_FRAME_MEDIA_TYPE

    if unchanged:
        # Keep cache fresh while avoiding duplicate writes/archive spam.
        with _LATEST_FRAME_LOCK:
            global _LATEST_FRAME_TS
            _LATEST_FRAME_TS = time.time()
        _AUTO_SYNC_LAST_OK_TS = time.time()
        _AUTO_SYNC_LAST_ERROR = ""
        _AUTO_SYNC_LAST_SOURCE = source_url
        if remote_seq:
            _LAST_REMOTE_FRAME_SEQ = remote_seq
        return False

    _save_latest_frame(content=image_bytes, media_type=media_type, archive=True)
    _AUTO_SYNC_LAST_OK_TS = time.time()
    _AUTO_SYNC_LAST_ERROR = ""
    _AUTO_SYNC_LAST_SOURCE = source_url
    if remote_seq:
        _LAST_REMOTE_FRAME_SEQ = remote_seq
    return True


def _esp32_auto_sync_loop() -> None:
    global _AUTO_SYNC_LAST_ERROR
    while True:
        try:
            if _auto_sync_enabled():
                _auto_sync_latest_frame_once()
        except Exception as exc:
            _AUTO_SYNC_LAST_ERROR = str(exc)
        time.sleep(_auto_sync_interval_seconds())


def _ensure_auto_sync_thread() -> None:
    global _AUTO_SYNC_THREAD
    with _AUTO_SYNC_THREAD_LOCK:
        if _AUTO_SYNC_THREAD is not None and _AUTO_SYNC_THREAD.is_alive():
            return
        _AUTO_SYNC_THREAD = threading.Thread(target=_esp32_auto_sync_loop, daemon=True, name="esp32-auto-sync")
        _AUTO_SYNC_THREAD.start()


_ensure_auto_sync_thread()

@router.post("/detect-plate")
async def detect_plate(file: UploadFile = File(...)):
    """
    Phát hiện biển số xe từ ảnh upload
    """
    try:
        # Đọc nội dung file ảnh
        content = await file.read()

        # Gọi hàm OCR để nhận diện biển số xe
        plate_text = await get_license_plate_text(content)

        if not plate_text:
            return {"success": False, "message": "Không nhận diện được biển số xe"}

        return {"success": True, "plate": plate_text}

    except Exception as e:
        return {"success": False, "message": f"Lỗi xử lý: {str(e)}"}


@router.get("/esp32/frame")
async def get_esp32_frame():
    _ensure_auto_sync_thread()
    now_ts = time.time()
    stale_after_seconds = float(os.getenv("ESP32_FRAME_STALE_SECONDS", "2.0"))
    cached = _get_cached_latest_frame()
    if cached is not None:
        image_bytes, media_type, frame_ts = cached
        if (now_ts - frame_ts) <= stale_after_seconds:
            return Response(content=image_bytes, media_type=media_type)

    push_only = os.getenv("ESP32_FRAME_USE_PUSH_ONLY", "1").strip().lower() not in {"0", "false", "no"}
    timeout_seconds = float(os.getenv("ESP32_CAPTURE_TIMEOUT_SECONDS", "4"))

    # Try live pull when cache is stale/missing.
    try:
        live_bytes, live_media_type, _, _ = _fetch_esp32_image_bytes(timeout_seconds=timeout_seconds)
        _save_latest_frame(content=live_bytes, media_type=live_media_type, archive=False)
        return Response(content=live_bytes, media_type=live_media_type)
    except HTTPException:
        # If live pull failed but we still have cached frame, return cache as degraded mode.
        if cached is not None:
            image_bytes, media_type, _ = cached
            return Response(content=image_bytes, media_type=media_type)
        if push_only:
            raise HTTPException(
                status_code=404,
                detail="Chua co frame moi tu ESP32. Bat backend + upload /api/camera/esp32/upload hoac kiem tra endpoint /latest.",
            )
        raise


@router.post("/esp32/upload")
async def upload_esp32_frame(file: UploadFile = File(default=None), request: Request = None):
    if file is not None:
        content = await file.read()
        media_type = file.content_type or "image/jpeg"
        if not content:
            raise HTTPException(status_code=400, detail="File anh rong.")
        return _save_latest_frame(content=content, media_type=media_type)

    if request is None:
        raise HTTPException(status_code=400, detail="Khong co noi dung upload.")

    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="Noi dung body rong.")

    media_type = request.headers.get("Content-Type", "image/jpeg")
    return _save_latest_frame(content=raw, media_type=media_type)


@router.get("/esp32/status")
async def get_esp32_status():
    _ensure_auto_sync_thread()
    base = _resolve_esp32_base_url()
    timeout_seconds = float(os.getenv("ESP32_CAPTURE_TIMEOUT_SECONDS", "4"))
    status_url = f"{base}/status"
    try:
        resp = requests.get(status_url, timeout=timeout_seconds)
        resp.raise_for_status()
        payload = resp.json()
        return {
            "ok": True,
            "esp32_base_url": base,
            "status_url": status_url,
            "upload_url": "/api/camera/esp32/upload",
            "frame_url": "/api/camera/esp32/frame",
            "auto_sync": {
                "enabled": _auto_sync_enabled(),
                "interval_seconds": _auto_sync_interval_seconds(),
                "last_ok_ts": _AUTO_SYNC_LAST_OK_TS,
                "last_error": _AUTO_SYNC_LAST_ERROR,
                "last_source": _AUTO_SYNC_LAST_SOURCE,
                "last_remote_frame_seq": _LAST_REMOTE_FRAME_SEQ,
            },
            "status": payload,
        }
    except Exception:
        return {
            "ok": False,
            "esp32_base_url": base,
            "status_url": status_url,
            "upload_url": "/api/camera/esp32/upload",
            "frame_url": "/api/camera/esp32/frame",
            "auto_sync": {
                "enabled": _auto_sync_enabled(),
                "interval_seconds": _auto_sync_interval_seconds(),
                "last_ok_ts": _AUTO_SYNC_LAST_OK_TS,
                "last_error": _AUTO_SYNC_LAST_ERROR,
                "last_source": _AUTO_SYNC_LAST_SOURCE,
                "last_remote_frame_seq": _LAST_REMOTE_FRAME_SEQ,
            },
            "message": "Khong doc duoc /status. Kiem tra ESP32-CAM va WiFi.",
        }