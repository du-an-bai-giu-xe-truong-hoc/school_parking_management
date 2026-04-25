from flask import Flask, request, jsonify
import os
import datetime

app = Flask(__name__)

# =======================================================
# 1. TẠO THƯ MỤC "capture" ĐỂ LƯU ẢNH TỰ ĐỘNG
# =======================================================
SAVE_DIR = "capture"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
    print(f"📁 Đã tạo thư mục mới: '{SAVE_DIR}' để chứa ảnh.")

# =======================================================
# 2. LẮNG NGHE ESP32 GỬI ẢNH LÊN
# =======================================================
@app.route('/api/esp32-upload', methods=['POST'])
def receive_image():
    print("\n🚗 [THÔNG BÁO] IR Sensor kích hoạt! Nhận ảnh từ ESP32...")
    
    # Kiểm tra dữ liệu ảnh từ ESP32 gửi lên
    if 'image' not in request.files:
        print("❌ Lỗi: Không tìm thấy file ảnh.")
        return jsonify({"status": "error", "message": "No image part"}), 400
        
    file = request.files['image']
    
    if file.filename == '':
        print("❌ Lỗi: File trống.")
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if file:
        # Tạo tên file theo thời gian (VD: cam_20260419_140500.jpg)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cam_{timestamp}.jpg"
        filepath = os.path.join(SAVE_DIR, filename)
        
        # LƯU ẢNH VÀO FOLDER "capture"
        file.save(filepath)
        print(f"✅ Đã lưu ảnh thành công vào: {filepath}")
        
        # Gửi lệnh phản hồi về cho ESP32 để MỞ CỔNG
        return jsonify({
            "status": "success", 
            "authorized": True, 
            "message": "Ảnh hợp lệ, cho phép mở cổng!"
        }), 200

if __name__ == '__main__':
    print("=====================================================")
    print("🖥️ SERVER PYTHON ĐANG CHẠY - HỆ THỐNG BÃI XE SẴN SÀNG")
    print(f"📁 Ảnh sẽ được tự động lưu vào folder: {os.path.abspath(SAVE_DIR)}")
    print("Đang lắng nghe dữ liệu từ ESP32 tại cổng 8000...")
    print("=====================================================")
    app.run(host='0.0.0.0', port=8000)