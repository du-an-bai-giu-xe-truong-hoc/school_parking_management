## 🌿 Chiến lược quản lý nhánh (Git Branching Strategy)

Để đảm bảo code của dự án **School Parking Management** luôn ổn định và dễ kiểm soát, chúng ta áp dụng mô hình Git Flow rút gọn:

### 1. Cấu trúc các nhánh chính
* **`main`**: Nhánh chính thức, chứa code đã hoàn thiện và ổn định nhất. Chỉ merge từ nhánh `develop` sau khi đã qua kiểm tra kỹ lưỡng.
* **`develop`**: Nhánh tích hợp các tính năng mới. Đây là nơi tập trung các code đang trong quá trình phát triển trước khi được release.

### 2. Các nhánh hỗ trợ
* **`feature/`**: Dùng để phát triển các tính năng hoặc module AI mới.
    * *Ví dụ:* `feature/yolov11-integration`, `feature/camera-api`, `feature/ocr-service`
* **`fix/`** hoặc **`bugfix/`**: Dùng để sửa lỗi được phát hiện trong quá trình phát triển.
    * *Ví dụ:* `fix/database-connection`, `fix/ocr-accuracy`

### 3. Quy trình làm việc (Workflow)

1.  **Cập nhật nhánh develop**: Trước khi bắt đầu, luôn lấy code mới nhất:
    ```bash
    git checkout develop
    git pull origin develop
    ```
2.  **Tạo nhánh mới**:
    ```bash
    git checkout -b feature/ten-tinh-nang
    ```
3.  **Làm việc và Commit**: Tuân thủ quy tắc viết commit message rõ ràng:
    ```bash
    git add .
    git commit -m "feat: thêm module nhận diện biển số bằng YOLOv11"
    ```
4.  **Đẩy code và tạo Pull Request (PR)**:
    ```bash
    git push origin feature/ten-tinh-nang
    ```
    *Sau đó, truy cập GitHub/GitLab để tạo PR vào nhánh `develop`. Team Leader hoặc thành viên khác sẽ review trước khi merge.*

---

## 📝 Quy ước đặt tên Commit (Commit Convention)

Sử dụng các tiền tố sau để dễ dàng theo dõi lịch sử:
* `feat:` Một tính năng mới.
* `fix:` Sửa lỗi.
* `docs:` Thay đổi tài liệu, file README.
* `refactor:` Tối ưu hóa code nhưng không đổi tính năng 
* `ai:` Các thay đổi liên quan đến training model hoặc dataset.

---
