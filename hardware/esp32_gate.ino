#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

// 1. CẤU HÌNH WIFI (Nên dùng WiFi phát từ điện thoại lúc đi thi cho ổn định)
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// 2. CẤU HÌNH PHẦN CỨNG (SERVO MOTOR)
Servo gateServo;
const int servoPin = 18;  // Chân GPIO trên ESP32 nối với dây tín hiệu của Servo
const int closeAngle = 0; // Góc khi Barie đóng
const int openAngle = 90; // Góc khi Barie mở

// 3. KHỞI TẠO WEB SERVER (Port 80 mặc định)
WebServer server(80);

void setup() {
  Serial.begin(115200);
  
  // Khởi tạo Barie ở trạng thái đóng
  gateServo.attach(servoPin);
  gateServo.write(closeAngle); 
  
  // Kết nối WiFi
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  // In ra IP để cài đặt vào backend FastAPI
  Serial.println("\n--- CONNECTED! ---");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.println("------------------");

  // Định tuyến API: Khi Backend gọi http://<IP_ESP32>/open -> Kích hoạt hàm handleOpenGate
  server.on("/open", HTTP_GET, handleOpenGate);
  
  // Bật khiên bảo vệ: Xử lý lỗi nếu gọi sai đường dẫn
  server.onNotFound([]() {
    server.send(404, "text/plain", "API Not Found");
  });

  server.begin();
  Serial.println("HTTP Server is running.");
}

void loop() {
  // Lắng nghe liên tục các request từ FastAPI gửi tới
  server.handleClient();
}

// 4. LOGIC XỬ LÝ MỞ CỔNG
void handleOpenGate() {
  Serial.println("[ACTION] Nhận lệnh MỞ CỔNG từ AI Server!");
  
  // Trả về response JSON cho FastAPI ngay lập tức để ngắt kết nối HTTP, tránh nghẽn
  server.send(200, "application/json", "{\"status\": \"success\", \"message\": \"Gate opened\"}");
  
  // Thực thi mở cổng
  gateServo.write(openAngle);
  
  // TRICK DEMO: Giữ cổng mở trong 3 giây để xe đi qua
  // Lưu ý: Dùng delay() sẽ block request khác trong 3s. Ở bản Demo thì chấp nhận được.
  // Ở bản Production, phải dùng millis() để quản lý thời gian bất đồng bộ.
  delay(3000); 
  
  // Tự động đóng cổng lại
  gateServo.write(closeAngle);
  Serial.println("[ACTION] Cổng đã đóng.");
}