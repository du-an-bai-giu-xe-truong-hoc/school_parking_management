import os

from fastapi.testclient import TestClient

from app.api import camera as camera_api
from app.main import app


def _payload(seq: int) -> bytes:
    # Synthetic JPEG-like bytes are enough for current media checks.
    return b"\xff\xd8\xff\xe0" + f"frame-{seq}".encode("utf-8") + os.urandom(128)


def test_esp32_upload_stress_and_latest_frame(tmp_path, monkeypatch):
    latest_path = tmp_path / "esp32_latest.jpg"
    archive_dir = tmp_path / "capture_archive"
    monkeypatch.setenv("ESP32_LATEST_FRAME_PATH", str(latest_path))
    monkeypatch.setenv("ESP32_CAPTURE_ARCHIVE_DIR", str(archive_dir))

    with camera_api._LATEST_FRAME_LOCK:
        camera_api._LATEST_FRAME_BYTES = b""
        camera_api._LATEST_FRAME_MEDIA_TYPE = "image/jpeg"
        camera_api._LATEST_FRAME_TS = 0.0

    client = TestClient(app)
    rounds = 30
    last_payload = b""

    for i in range(rounds):
        body = _payload(i)
        last_payload = body
        resp = client.post(
            "/api/camera/esp32/upload",
            content=body,
            headers={"Content-Type": "image/jpeg"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is True
        assert payload["bytes"] == len(body)

    frame_resp = client.get("/api/camera/esp32/frame")
    assert frame_resp.status_code == 200
    assert frame_resp.headers["content-type"].startswith("image/jpeg")
    assert frame_resp.content == last_payload

    assert latest_path.exists()
    assert latest_path.read_bytes() == last_payload
    archived = list(archive_dir.glob("cam_*.jpg"))
    assert len(archived) >= rounds


def test_esp32_upload_rejects_empty_raw_body(tmp_path, monkeypatch):
    monkeypatch.setenv("ESP32_LATEST_FRAME_PATH", str(tmp_path / "esp32_latest.jpg"))
    monkeypatch.setenv("ESP32_CAPTURE_ARCHIVE_DIR", str(tmp_path / "capture_archive"))

    client = TestClient(app)
    resp = client.post(
        "/api/camera/esp32/upload",
        content=b"",
        headers={"Content-Type": "image/jpeg"},
    )
    assert resp.status_code == 400
    assert "rong" in resp.json()["detail"].lower()