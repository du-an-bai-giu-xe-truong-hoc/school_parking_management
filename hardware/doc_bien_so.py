import os
import glob
from pathlib import Path
from google.cloud import vision

# =======================================================
# 1. NẠP CHÌA KHÓA GOOGLE CLOUD (JSON KEY)
# Đảm bảo file gg_cloud_key.json nằm cùng thư mục với file code này
# =======================================================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
GOOGLE_KEY_PATH = BASE_DIR / "gg_cloud_key.json"
CAPTURE_DIR = PROJECT_ROOT / "capture"

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(GOOGLE_KEY_PATH)

def doc_bien_so_gg_cloud(image_path):
    print(f"🔍 Đang gửi ảnh lên Google Cloud Vision: {image_path}...")
    
    # Khởi tạo "người đưa thư" của Google
    client = vision.ImageAnnotatorClient()

    # Đọc file ảnh từ ổ cứng lên
    with open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    # Gọi API trích xuất văn bản (Text Detection)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    # Xử lý nếu Google báo lỗi (ví dụ: hết tiền, sai key...)
    if response.error.message:
        print(f"❌ Lỗi từ Google Cloud: {response.error.message}")
        return None

    # Nếu tìm thấy chữ trong ảnh
    if texts:
        # texts[0].description sẽ chứa TOÀN BỘ đoạn text mà nó quét được ghép lại
        bien_so = texts[0].description.strip()
        print("\n✅ KẾT QUẢ ĐỌC ĐƯỢC TỪ ẢNH:")
        print("========================")
        print(bien_so)
        print("========================")
        return bien_so
    else:
        print("⚠️ Không tìm thấy bất kỳ chữ/số nào trong ảnh.")
        return None

if __name__ == '__main__':
    # Tìm file ảnh mới nhất trong thư mục "capture"
    thu_muc_anh = str(CAPTURE_DIR)
    
    if not os.path.exists(thu_muc_anh):
        print(f"❌ Không tìm thấy thư mục '{thu_muc_anh}'. Hãy chạy server_nhan_anh.py để quẹt tay chụp một tấm trước nhé.")
    else:
        # Lấy danh sách tất cả file .jpg, sắp xếp theo thời gian tạo mới nhất
        danh_sach_anh = glob.glob(os.path.join(thu_muc_anh, '*.jpg')) + glob.glob(os.path.join(thu_muc_anh, '*.png'))
        
        if not danh_sach_anh:
            print(f"❌ Thư mục '{thu_muc_anh}' đang trống. Hãy kích hoạt cảm biến IR để chụp ảnh đi Nhật ơi!")
        else:
            anh_moi_nhat = max(danh_sach_anh, key=os.path.getctime)
            
            # Gọi hàm tiến hành đọc chữ
            doc_bien_so_gg_cloud(anh_moi_nhat)