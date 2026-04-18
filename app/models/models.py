"""SQLAlchemy models for the parking management domain."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    identity_card = Column(String(20), unique=True, nullable=False)
    phone_number = Column(String(15))
    balance = Column(Float, default=50000.0, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    vehicles = relationship("Vehicle", back_populates="owner")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    license_plate = Column(String(20), unique=True, nullable=False)
    vehicle_type = Column(String(50), nullable=False)
    color = Column(String(50), nullable=True)
    is_locked = Column(Boolean, default=False, nullable=False)
    lock_reason = Column(String(255), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="vehicles")
    transactions = relationship("Transaction", back_populates="vehicle")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    time_in = Column(DateTime, default=datetime.now)
    time_out = Column(DateTime, nullable=True)
    status = Column(String(20), default="Parked")
    fee = Column(Float, default=0.0)
    lane = Column(String(20), nullable=True)
    barcode_raw = Column(Text, nullable=True)
    scanned_plate = Column(String(30), nullable=True)
    entry_iot_image_path = Column(String(255), nullable=True)
    exit_iot_image_path = Column(String(255), nullable=True)
    entry_local_image_path = Column(String(255), nullable=True)
    exit_local_image_path = Column(String(255), nullable=True)
    image_similarity_score = Column(Float, default=0.0, nullable=False)
    alert_flag = Column(Boolean, default=False, nullable=False)

    vehicle = relationship("Vehicle", back_populates="transactions")