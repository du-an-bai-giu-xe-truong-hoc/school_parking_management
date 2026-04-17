# ==========================================
# FILE: app/models/models.py
# MỤC ĐÍCH: Định nghĩa cấu trúc các bảng trong Database
# ==========================================
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

# Khởi tạo Base để các class kế thừa
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False) 
    identity_card = Column(String(20), unique=True, nullable=False) 
    phone_number = Column(String(15))
    created_at = Column(DateTime, default=datetime.now)
    vehicles = relationship("Vehicle", back_populates="owner")

class Vehicle(Base):
    __tablename__ = 'vehicles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    license_plate = Column(String(20), unique=True, nullable=False) 
    vehicle_type = Column(String(50), nullable=False) 
    color = Column(String(50)) # <-- PHẢI CÓ DÒNG NÀY ĐỂ KHỚP VỚI SQL SERVER
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    owner = relationship("User", back_populates="vehicles")
    transactions = relationship("Transaction", back_populates="vehicle")

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), nullable=False)
    time_in = Column(DateTime, default=datetime.now, nullable=False)
    time_out = Column(DateTime, nullable=True) 
    status = Column(String(20), default='Parked') 
    fee = Column(Float, default=0.0)
    vehicle = relationship("Vehicle", back_populates="transactions")