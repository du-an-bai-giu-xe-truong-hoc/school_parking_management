"""Parking service with dual-camera capture, wallet checking, and security rules."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
import requests
from sqlalchemy.orm import Session

from app.models.models import Transaction, User, Vehicle
from app.services.fee_service import calculate_duration_fee, calculate_parking_fee
from app.services.ocr_service import extract_plate_text_with_yolo_vision

logger = logging.getLogger(__name__)


class ParkingService:
    MIN_STRING_MATCH_SCORE = 70.0
    MIN_IMAGE_MATCH_SCORE = 70.0
    ENTRY_GATE_OPEN_SECONDS = 10
    EXIT_GATE_OPEN_SECONDS = 10

    def __init__(self):
        self.capture_url = os.getenv("ESP32_CAPTURE_URL", "http://192.168.101.8/capture")
        self.capture_timeout = float(os.getenv("ESP32_CAPTURE_TIMEOUT_SECONDS", "4"))
        self.storage_root = Path(os.getenv("PARKING_CAPTURE_DIR", "app/storage/captures"))
        self.storage_root.mkdir(parents=True, exist_ok=True)

    async def process_vehicle_request(
        self,
        db: Session,
        qr_code: str,
        gate_type: str,
        bien_so: str = "",
    ) -> Dict[str, Any]:
        gate = (gate_type or "").strip().upper()
        if gate == "VAO":
            return await self.process_entry(db=db, qr_code=qr_code, bien_so=bien_so)
        if gate == "RA":
            return await self.process_exit(db=db, qr_code=qr_code, bien_so=bien_so)
        return self._build_result(
            status="failed",
            action="ERROR",
            message="Loai cong khong hop le. Chi chap nhan 'VAO' hoac 'RA'.",
            decision="deny",
            barcode_payload={"raw": qr_code},
            scanned_plate=bien_so,
        )

    async def preview_vehicle(self, db: Session, qr_code: str, bien_so: str = "") -> Dict[str, Any]:
        payload = self._decode_barcode_payload(qr_code)
        vehicle, _ = self._resolve_vehicle(db, payload, self._normalize_plate(bien_so))
        if vehicle is None:
            return {
                "status": "failed",
                "message": "Khong tim thay du lieu xe tu barcode trong database.",
                "vehicle_id": None,
                "db_license_plate": None,
                "owner_name": None,
                "owner_identity_card": None,
                "owner_balance": None,
                "vehicle_locked": None,
                "lock_reason": None,
            }

        owner = vehicle.owner
        active_transaction = (
            db.query(Transaction)
            .filter(
                Transaction.vehicle_id == vehicle.id,
                Transaction.status == "Parked",
                Transaction.time_out.is_(None),
            )
            .order_by(Transaction.time_in.desc())
            .first()
        )
        return {
            "status": "success",
            "message": "Da doi soat du lieu xe tu database.",
            "vehicle_id": vehicle.id,
            "db_license_plate": vehicle.license_plate,
            "owner_name": owner.full_name if owner else None,
            "owner_identity_card": owner.identity_card if owner else None,
            "owner_balance": float(owner.balance or 0.0) if owner else None,
            "vehicle_locked": bool(vehicle.is_locked),
            "lock_reason": vehicle.lock_reason,
            "time_in": active_transaction.time_in if active_transaction else datetime.now().replace(hour=7, minute=0, second=0, microsecond=0),
        }

    async def process_entry(
        self,
        db: Session,
        qr_code: str,
        bien_so: str,
        lane: Optional[str] = None,
        local_image_base64: Optional[str] = None,
    ) -> Dict[str, Any]:
        barcode_payload = self._decode_barcode_payload(qr_code)
        local_image_bytes = self._decode_base64_image(local_image_base64)
        detected_plate = (bien_so or "").strip()
        if local_image_bytes:
            yolo_vision_plate = await extract_plate_text_with_yolo_vision(local_image_bytes)
            if yolo_vision_plate:
                detected_plate = yolo_vision_plate

        normalized_scan = self._normalize_plate(detected_plate)

        if not qr_code:
            return self._build_result(
                status="failed",
                action="ERROR",
                message="Thieu ma barcode/QR cho xe vao.",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
            )

        if not normalized_scan:
            return self._build_result(
                status="failed",
                action="ERROR",
                message="Khong doc duoc bien so tu YOLOv8 + Google Vision. Vui long thu lai.",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
            )

        vehicle, _ = self._resolve_vehicle(db, barcode_payload, normalized_scan)
        if vehicle is None:
            return self._build_result(
                status="failed",
                action="NOT_FOUND",
                message="Khong tim thay xe trong database tu barcode va bien so quet.",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
            )

        owner = vehicle.owner
        score_scan_vs_db = self._fuzzy_score(normalized_scan, self._normalize_plate(vehicle.license_plate))
        if score_scan_vs_db < self.MIN_STRING_MATCH_SCORE:
            return self._build_result(
                status="failed",
                action="DENY_ENTRY",
                message="Ti le khop bien so thap, yeu cau xac minh thu cong.",
                decision="manual_review",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
                vehicle=vehicle,
                owner=owner,
                similarity_score=score_scan_vs_db,
                string_similarity_score=score_scan_vs_db,
            )

        active_transaction = (
            db.query(Transaction)
            .filter(
                Transaction.vehicle_id == vehicle.id,
                Transaction.status == "Parked",
                Transaction.time_out.is_(None),
            )
            .order_by(Transaction.time_in.desc())
            .first()
        )
        if active_transaction is not None:
            return self._build_result(
                status="failed",
                action="ALREADY_PARKED",
                message="Xe nay dang co luot gui xe hoat dong.",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
                vehicle=vehicle,
                owner=owner,
                transaction=active_transaction,
                similarity_score=score_scan_vs_db,
                string_similarity_score=score_scan_vs_db,
            )

        transaction = Transaction(
            vehicle_id=vehicle.id,
            time_in=datetime.now(),
            status="Parked",
            fee=0.0,
            lane=lane,
            barcode_raw=qr_code,
            scanned_plate=detected_plate,
        )
        db.add(transaction)
        db.flush()

        try:
            entry_iot_image_path = self._capture_iot_image("entry_iot", vehicle.license_plate, transaction.id)
        except TimeoutError as e:
            db.rollback()
            return self._build_result(
                status="failed",
                action="CAMERA_TIMEOUT",
                message=str(e),
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
                vehicle=vehicle,
                owner=owner,
                similarity_score=score_scan_vs_db,
                string_similarity_score=score_scan_vs_db,
            )
        entry_local_image_path = self._store_local_image_bytes(
            local_image_bytes,
            "entry_local",
            vehicle.license_plate,
            transaction.id,
        )

        transaction.entry_iot_image_path = entry_iot_image_path
        transaction.entry_local_image_path = entry_local_image_path
        db.commit()
        db.refresh(transaction)

        return self._build_result(
            status="success",
            action="OPEN_GATE_IN",
            message="Xe vao hop le. He thong da mo barrier 10s.",
            decision="allow",
            barcode_payload=barcode_payload,
            scanned_plate=detected_plate,
            vehicle=vehicle,
            owner=owner,
            transaction=transaction,
            similarity_score=score_scan_vs_db,
            string_similarity_score=score_scan_vs_db,
            image_similarity_score=None,
            gate_open_seconds=self.ENTRY_GATE_OPEN_SECONDS,
            entry_iot_image_path=entry_iot_image_path,
            exit_iot_image_path=None,
            entry_local_image_path=entry_local_image_path,
            exit_local_image_path=None,
        )

    async def process_exit(
        self,
        db: Session,
        qr_code: str,
        bien_so: str,
        lane: Optional[str] = None,
        local_image_base64: Optional[str] = None,
    ) -> Dict[str, Any]:
        barcode_payload = self._decode_barcode_payload(qr_code)
        local_image_bytes = self._decode_base64_image(local_image_base64)
        detected_plate = (bien_so or "").strip()
        if local_image_bytes:
            yolo_vision_plate = await extract_plate_text_with_yolo_vision(local_image_bytes)
            if yolo_vision_plate:
                detected_plate = yolo_vision_plate

        normalized_scan = self._normalize_plate(detected_plate)

        if not qr_code:
            return self._build_result(
                status="failed",
                action="ERROR",
                message="Thieu ma barcode/QR cho xe ra.",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
            )

        if not normalized_scan:
            return self._build_result(
                status="failed",
                action="ERROR",
                message="Khong doc duoc bien so tu YOLOv8 + Google Vision. Vui long thu lai.",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
            )

        vehicle, _ = self._resolve_vehicle(db, barcode_payload, normalized_scan)
        if vehicle is None:
            return self._build_result(
                status="failed",
                action="NOT_FOUND",
                message="Khong xac dinh duoc xe ra tu barcode va bien so quet.",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
            )

        owner = vehicle.owner
        active_transaction = (
            db.query(Transaction)
            .filter(
                Transaction.vehicle_id == vehicle.id,
                Transaction.status == "Parked",
                Transaction.time_out.is_(None),
            )
            .order_by(Transaction.time_in.desc())
            .first()
        )
        if active_transaction is None:
            # MVP: Tự động tạo giao dịch vào giả lập với thời gian mẫu
            mock_time_in = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
            if mock_time_in > datetime.now():
                mock_time_in = datetime.now() - timedelta(hours=4)
                
            active_transaction = Transaction(
                vehicle_id=vehicle.id,
                time_in=mock_time_in,
                status="Parked",
                fee=0.0,
                lane=lane,
                barcode_raw=qr_code,
                scanned_plate=detected_plate,
            )
            db.add(active_transaction)
            db.flush()

        try:
            exit_iot_image_path = self._capture_iot_image("exit_iot", vehicle.license_plate, active_transaction.id)
        except TimeoutError as e:
            return self._build_result(
                status="failed",
                action="CAMERA_TIMEOUT",
                message=str(e),
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
                vehicle=vehicle,
                owner=owner,
                transaction=active_transaction,
            )
        exit_local_image_path = self._store_local_image_bytes(
            local_image_bytes,
            "exit_local",
            vehicle.license_plate,
            active_transaction.id,
        )
        active_transaction.exit_iot_image_path = exit_iot_image_path
        active_transaction.exit_local_image_path = exit_local_image_path
        active_transaction.scanned_plate = detected_plate
        active_transaction.barcode_raw = qr_code
        active_transaction.lane = lane or active_transaction.lane

        if bool(vehicle.is_locked):
            active_transaction.alert_flag = True
            db.commit()
            return self._build_result(
                status="failed",
                action="ALERT_SECURITY",
                message="Xe dang o trang thai khoa. Da kich hoat canh bao bao ve.",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
                vehicle=vehicle,
                owner=owner,
                transaction=active_transaction,
                similarity_score=0.0,
                string_similarity_score=0.0,
                image_similarity_score=0.0,
                alert_security=True,
                entry_iot_image_path=active_transaction.entry_iot_image_path,
                exit_iot_image_path=exit_iot_image_path,
                entry_local_image_path=active_transaction.entry_local_image_path,
                exit_local_image_path=exit_local_image_path,
            )

        db_plate_normalized = self._normalize_plate(vehicle.license_plate)
        score_scan_vs_db = self._fuzzy_score(normalized_scan, db_plate_normalized)
        barcode_plate = self._extract_plate_from_payload(barcode_payload) or vehicle.license_plate
        score_barcode_vs_db = self._fuzzy_score(self._normalize_plate(barcode_plate), db_plate_normalized)
        string_similarity = round((score_scan_vs_db + score_barcode_vs_db) / 2.0, 2)

        if string_similarity < self.MIN_STRING_MATCH_SCORE:
            db.commit()
            return self._build_result(
                status="failed",
                action="DENY_EXIT_STRING",
                message="Do khop chuoi barcode/bien so thap. Thu lai!",
                decision="manual_review",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
                vehicle=vehicle,
                owner=owner,
                transaction=active_transaction,
                similarity_score=string_similarity,
                string_similarity_score=string_similarity,
                image_similarity_score=None,
                entry_iot_image_path=active_transaction.entry_iot_image_path,
                exit_iot_image_path=exit_iot_image_path,
                entry_local_image_path=active_transaction.entry_local_image_path,
                exit_local_image_path=exit_local_image_path,
            )

        entry_reference = active_transaction.entry_iot_image_path or active_transaction.entry_local_image_path
        exit_reference = exit_iot_image_path or exit_local_image_path
        image_similarity = self._image_similarity(entry_reference, exit_reference)

        if entry_reference is None or exit_reference is None:
            db.commit()
            return self._build_result(
                status="failed",
                action="IMAGE_COMPARE_MISSING",
                message="Thieu anh de doi soat. Khong duoc mo cong. Thu lai!",
                decision="manual_review",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
                vehicle=vehicle,
                owner=owner,
                transaction=active_transaction,
                similarity_score=string_similarity,
                string_similarity_score=string_similarity,
                image_similarity_score=image_similarity,
                entry_iot_image_path=active_transaction.entry_iot_image_path,
                exit_iot_image_path=exit_iot_image_path,
                entry_local_image_path=active_transaction.entry_local_image_path,
                exit_local_image_path=exit_local_image_path,
            )

        if image_similarity < self.MIN_IMAGE_MATCH_SCORE:
            db.commit()
            return self._build_result(
                status="failed",
                action="DENY_EXIT_IMAGE",
                message="Ty le giong nhau cua 2 hinh anh duoi 70%. Khong cho ra cong. Thu lai!",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
                vehicle=vehicle,
                owner=owner,
                transaction=active_transaction,
                similarity_score=image_similarity,
                string_similarity_score=string_similarity,
                image_similarity_score=image_similarity,
                entry_iot_image_path=active_transaction.entry_iot_image_path,
                exit_iot_image_path=exit_iot_image_path,
                entry_local_image_path=active_transaction.entry_local_image_path,
                exit_local_image_path=exit_local_image_path,
            )

        now = datetime.now()
        duration_minutes = int(max((now - active_transaction.time_in).total_seconds(), 0) // 60)
        base_fee = float(calculate_parking_fee(vehicle.vehicle_type))
        duration_fee = float(calculate_duration_fee(active_transaction.time_in, now))
        total_fee = round(base_fee + duration_fee, 2)

        current_balance = float(owner.balance or 0.0) if owner else 0.0
        if owner is None or current_balance < total_fee:
            db.commit()
            return self._build_result(
                status="failed",
                action="INSUFFICIENT_BALANCE",
                message="Tai khoan khong du tien. Vui long lui xe va qua cong khac.",
                decision="deny",
                barcode_payload=barcode_payload,
                scanned_plate=detected_plate,
                vehicle=vehicle,
                owner=owner,
                transaction=active_transaction,
                similarity_score=min(string_similarity, image_similarity),
                string_similarity_score=string_similarity,
                image_similarity_score=image_similarity,
                fee=total_fee,
                duration_minutes=duration_minutes,
                insufficient_balance=True,
                entry_iot_image_path=active_transaction.entry_iot_image_path,
                exit_iot_image_path=exit_iot_image_path,
                entry_local_image_path=active_transaction.entry_local_image_path,
                exit_local_image_path=exit_local_image_path,
            )

        owner.balance = round(current_balance - total_fee, 2)
        active_transaction.time_out = now
        active_transaction.status = "Completed"
        active_transaction.fee = total_fee
        active_transaction.image_similarity_score = image_similarity
        active_transaction.alert_flag = False
        db.commit()
        db.refresh(active_transaction)
        db.refresh(owner)

        overall_similarity = round((string_similarity + image_similarity) / 2.0, 2)
        return self._build_result(
            status="success",
            action="OPEN_GATE_OUT",
            message="Xe ra hop le. Da tru tien va mo barrier 10s.",
            decision="allow",
            barcode_payload=barcode_payload,
            scanned_plate=detected_plate,
            vehicle=vehicle,
            owner=owner,
            transaction=active_transaction,
            similarity_score=overall_similarity,
            string_similarity_score=string_similarity,
            image_similarity_score=image_similarity,
            fee=total_fee,
            duration_minutes=duration_minutes,
            gate_open_seconds=self.EXIT_GATE_OPEN_SECONDS,
            entry_iot_image_path=active_transaction.entry_iot_image_path,
            exit_iot_image_path=exit_iot_image_path,
            entry_local_image_path=active_transaction.entry_local_image_path,
            exit_local_image_path=exit_local_image_path,
        )

    def get_history(self, db: Session, skip: int = 0, limit: int = 200) -> list[Dict[str, Any]]:
        rows = (
            db.query(Transaction, Vehicle, User)
            .join(Vehicle, Vehicle.id == Transaction.vehicle_id)
            .join(User, User.id == Vehicle.owner_id)
            .order_by(Transaction.time_in.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        history: list[Dict[str, Any]] = []
        for transaction, vehicle, user in rows:
            history.append(
                {
                    "transaction_id": transaction.id,
                    "vehicle_id": vehicle.id,
                    "license_plate": vehicle.license_plate,
                    "owner_name": user.full_name,
                    "identity_card": user.identity_card,
                    "owner_balance": float(user.balance or 0.0),
                    "vehicle_type": vehicle.vehicle_type,
                    "time_in": transaction.time_in,
                    "time_out": transaction.time_out,
                    "status": transaction.status,
                    "fee": float(transaction.fee or 0.0),
                    "lane": transaction.lane,
                    "image_similarity_score": float(transaction.image_similarity_score or 0.0),
                    "alert_flag": bool(transaction.alert_flag),
                }
            )
        return history

    def get_active_transactions(self, db: Session, limit: int = 200) -> list[Dict[str, Any]]:
        rows = (
            db.query(Transaction, Vehicle, User)
            .join(Vehicle, Vehicle.id == Transaction.vehicle_id)
            .join(User, User.id == Vehicle.owner_id)
            .filter(Transaction.status == "Parked", Transaction.time_out.is_(None))
            .order_by(Transaction.time_in.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "transaction_id": transaction.id,
                "vehicle_id": vehicle.id,
                "license_plate": vehicle.license_plate,
                "owner_name": user.full_name,
                "identity_card": user.identity_card,
                "owner_balance": float(user.balance or 0.0),
                "vehicle_type": vehicle.vehicle_type,
                "vehicle_locked": bool(vehicle.is_locked),
                "time_in": transaction.time_in,
                "status": transaction.status,
                "fee": float(transaction.fee or 0.0),
                "lane": transaction.lane,
            }
            for transaction, vehicle, user in rows
        ]

    def _build_result(
        self,
        *,
        status: str,
        action: str,
        message: str,
        decision: str,
        barcode_payload: Dict[str, Any],
        scanned_plate: Optional[str],
        vehicle: Optional[Vehicle] = None,
        owner: Optional[User] = None,
        transaction: Optional[Transaction] = None,
        similarity_score: float = 0.0,
        string_similarity_score: Optional[float] = None,
        image_similarity_score: Optional[float] = None,
        fee: Optional[float] = None,
        duration_minutes: Optional[int] = None,
        alert_security: bool = False,
        insufficient_balance: bool = False,
        gate_open_seconds: int = 0,
        entry_iot_image_path: Optional[str] = None,
        exit_iot_image_path: Optional[str] = None,
        entry_local_image_path: Optional[str] = None,
        exit_local_image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "status": status,
            "action": action,
            "message": message,
            "decision": decision,
            "similarity_score": round(float(similarity_score), 2),
            "threshold": self.MIN_STRING_MATCH_SCORE,
            "transaction_id": transaction.id if transaction else None,
            "vehicle_id": vehicle.id if vehicle else None,
            "db_license_plate": vehicle.license_plate if vehicle else None,
            "scanned_plate": scanned_plate,
            "time_in": transaction.time_in if transaction else None,
            "time_out": transaction.time_out if transaction else None,
            "duration_minutes": duration_minutes,
            "fee": fee if fee is not None else (float(transaction.fee or 0.0) if transaction else None),
            "string_similarity_score": string_similarity_score,
            "image_similarity_score": image_similarity_score,
            "owner_name": owner.full_name if owner else None,
            "owner_identity_card": owner.identity_card if owner else None,
            "owner_balance": float(owner.balance or 0.0) if owner else None,
            "vehicle_locked": bool(vehicle.is_locked) if vehicle else False,
            "lock_reason": vehicle.lock_reason if vehicle else None,
            "alert_security": alert_security,
            "insufficient_balance": insufficient_balance,
            "gate_open_seconds": gate_open_seconds,
            "entry_iot_image_path": entry_iot_image_path
            if entry_iot_image_path is not None
            else (transaction.entry_iot_image_path if transaction else None),
            "exit_iot_image_path": exit_iot_image_path
            if exit_iot_image_path is not None
            else (transaction.exit_iot_image_path if transaction else None),
            "entry_local_image_path": entry_local_image_path
            if entry_local_image_path is not None
            else (transaction.entry_local_image_path if transaction else None),
            "exit_local_image_path": exit_local_image_path
            if exit_local_image_path is not None
            else (transaction.exit_local_image_path if transaction else None),
            "barcode_payload": barcode_payload,
        }
        return result

    def _capture_iot_image(self, prefix: str, plate: str, transaction_id: Optional[int]) -> Optional[str]:
        try:
            response = requests.get(self.capture_url, timeout=self.capture_timeout)
            response.raise_for_status()
            if not response.content:
                return None
            return self._save_image_bytes(response.content, prefix, plate, transaction_id)
        except requests.exceptions.Timeout:
            logger.warning("Timeout when capturing IoT image from %s", self.capture_url)
            raise TimeoutError("Lỗi: Mất kết nối tới Camera IoT. Vui lòng kiểm tra cáp mạng hoặc dùng nút Mở Khẩn Cấp!")
        except Exception as exc:
            logger.warning("Cannot capture IoT image from %s: %s", self.capture_url, exc)
            return None

    def _store_local_image(
        self,
        local_image_base64: Optional[str],
        prefix: str,
        plate: str,
        transaction_id: Optional[int],
    ) -> Optional[str]:
        if not local_image_base64:
            return None

        image_bytes = self._decode_base64_image(local_image_base64)
        return self._store_local_image_bytes(image_bytes, prefix, plate, transaction_id)

    def _store_local_image_bytes(
        self,
        image_bytes: Optional[bytes],
        prefix: str,
        plate: str,
        transaction_id: Optional[int],
    ) -> Optional[str]:
        if image_bytes is None:
            return None
        return self._save_image_bytes(image_bytes, prefix, plate, transaction_id)

    def _decode_base64_image(self, value: str) -> Optional[bytes]:
        if not value:
            return None
        raw = value.strip()
        if not raw:
            return None

        if "," in raw and raw.lower().startswith("data:image"):
            raw = raw.split(",", 1)[1]

        try:
            return base64.b64decode(raw)
        except Exception:
            return None

    def _save_image_bytes(
        self,
        image_bytes: bytes,
        prefix: str,
        plate: str,
        transaction_id: Optional[int],
    ) -> Optional[str]:
        if not image_bytes:
            return None

        day_folder = self.storage_root / datetime.now().strftime("%Y%m%d")
        day_folder.mkdir(parents=True, exist_ok=True)

        safe_plate = re.sub(r"[^A-Za-z0-9]", "", plate.upper()) or "UNKNOWN"
        tx = str(transaction_id) if transaction_id is not None else "NA"
        filename = f"{prefix}_{safe_plate}_tx{tx}_{datetime.now().strftime('%H%M%S%f')}.jpg"
        output_path = day_folder / filename

        try:
            output_path.write_bytes(image_bytes)
            return output_path.as_posix()
        except Exception as exc:
            logger.warning("Cannot save capture image %s: %s", output_path, exc)
            return None

    def _image_similarity(self, path_a: Optional[str], path_b: Optional[str]) -> float:
        if not path_a or not path_b:
            return 0.0

        image_a = cv2.imread(path_a, cv2.IMREAD_GRAYSCALE)
        image_b = cv2.imread(path_b, cv2.IMREAD_GRAYSCALE)
        if image_a is None or image_b is None:
            return 0.0

        image_a = cv2.resize(image_a, (320, 240))
        image_b = cv2.resize(image_b, (320, 240))

        diff = cv2.absdiff(image_a, image_b)
        mae = float(np.mean(diff)) / 255.0
        score = max(0.0, min(100.0, (1.0 - mae) * 100.0))
        return round(score, 2)

    def _decode_barcode_payload(self, qr_code: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"raw": qr_code or ""}
        if not qr_code:
            return payload

        raw = qr_code.strip()
        if not raw:
            return payload

        try:
            parsed_json = json.loads(raw)
            if isinstance(parsed_json, dict):
                payload.update(parsed_json)
                return payload
        except json.JSONDecodeError:
            pass

        parsed_pairs: Dict[str, Any] = {}
        for chunk in re.split(r"[;|]", raw):
            item = chunk.strip()
            if not item:
                continue

            if "=" in item:
                key, value = item.split("=", 1)
            elif ":" in item:
                key, value = item.split(":", 1)
            else:
                continue

            parsed_pairs[key.strip().lower()] = value.strip()

        if parsed_pairs:
            payload.update(parsed_pairs)
        else:
            payload["value"] = raw

        return payload

    def _extract_plate_from_payload(self, payload: Dict[str, Any]) -> Optional[str]:
        for key in ("license_plate", "bien_so", "plate", "plate_number"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        value = payload.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _resolve_vehicle(
        self,
        db: Session,
        payload: Dict[str, Any],
        normalized_scan: str,
    ) -> Tuple[Optional[Vehicle], str]:
        vehicle_id = self._as_int(payload.get("vehicle_id") or payload.get("id"))
        if vehicle_id is not None:
            vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if vehicle is not None:
                return vehicle, "vehicle_id"

        barcode_plate = self._extract_plate_from_payload(payload)
        if barcode_plate:
            vehicle = self._get_vehicle_by_normalized_plate(db, self._normalize_plate(barcode_plate))
            if vehicle is not None:
                return vehicle, "barcode_plate"

        identity_card = payload.get("identity_card") or payload.get("student_id") or payload.get("owner_code")
        if isinstance(identity_card, str) and identity_card.strip():
            vehicle = (
                db.query(Vehicle)
                .join(User, User.id == Vehicle.owner_id)
                .filter(User.identity_card == identity_card.strip())
                .first()
            )
            if vehicle is not None:
                return vehicle, "identity_card"

        if normalized_scan:
            vehicle = self._get_vehicle_by_normalized_plate(db, normalized_scan)
            if vehicle is not None:
                return vehicle, "scan_plate"

        return None, "unresolved"

    def _get_vehicle_by_normalized_plate(self, db: Session, normalized_plate: str) -> Optional[Vehicle]:
        if not normalized_plate:
            return None

        vehicles = db.query(Vehicle).all()
        for vehicle in vehicles:
            if self._normalize_plate(vehicle.license_plate) == normalized_plate:
                return vehicle
        return None

    def _normalize_plate(self, text: Optional[str]) -> str:
        return re.sub(r"[^A-Z0-9]", "", (text or "").upper())

    def _fuzzy_score(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return round(SequenceMatcher(None, left, right).ratio() * 100.0, 2)

    def _as_int(self, value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None


parking_service = ParkingService()
