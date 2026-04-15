# 1. Nhập thực thể Base từ models (Nơi chứa mã định danh chung)
from app.models.models import Base 

# 2. Nhập toàn bộ các Model (Bảng) để SQLAlchemy nhận diện
# Điều này cực kỳ quan trọng đối với các công cụ như Alembic 
# hoặc khi chạy lệnh tạo bảng tự động.
from app.models.models import User, Vehicle, Transaction