import sys
import os
import logging
from datetime import datetime, timedelta

# Thêm thư mục gốc của project vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.models import Transaction

# Cấu hình thư mục logs
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'cleanup.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def delete_file_if_exists(filepath: str):
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
            logger.info(f"Đã xoá: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xoá {filepath}: {e}")
    elif filepath:
        pass
    return False

def cleanup_old_images(days=30):
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"Bắt đầu dọn dẹp ảnh cho các giao dịch trước ngày {cutoff_date}")

        transactions = db.query(Transaction).filter(
            Transaction.time_in < cutoff_date,
            Transaction.alert_flag == False
        ).all()

        deleted_count = 0
        for txn in transactions:
            cleaned = False
            for attr in ['entry_iot_image_path', 'exit_iot_image_path', 'entry_local_image_path', 'exit_local_image_path']:
                filepath = getattr(txn, attr)
                if filepath:
                    if not os.path.isabs(filepath):
                        filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filepath)

                    if delete_file_if_exists(filepath):
                        setattr(txn, attr, None)
                        cleaned = True
                    else:
                        if not os.path.exists(filepath):
                            setattr(txn, attr, None)
                            cleaned = True

            if cleaned:
                deleted_count += 1

        db.commit()
        logger.info(f"Hoàn thành dọn dẹp. Đã xử lý ảnh của {deleted_count} giao dịch.")

    except Exception as e:
        logger.error(f"Lỗi trong quá trình dọn dẹp: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    days = 30
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        days = int(sys.argv[1])
    cleanup_old_images(days)
