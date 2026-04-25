/**
 * ============================================================
 * HỆ THỐNG BARRIER TỰ ĐỘNG - ESP32-CAM (AI Thinker)
 * Phiên bản: 2.5 (Hoàn chỉnh - Tích hợp AI FastAPI + Fix BOD + Servo)
 * ============================================================
 */

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include "esp_camera.h"
#include "esp_task_wdt.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#if __has_include(<esp_arduino_version.h>)
#include <esp_arduino_version.h>
#endif

// ============================================================
// 1. CẤU HÌNH WIFI & BACKEND
// ============================================================
const char* WIFI_SSID     = "QUYNH ANH T3";
const char* WIFI_PASSWORD = "milksua1302";

// Địa chỉ IP của máy tính đang chạy FastAPI
const char* BACKEND_HOST = "192.168.101.7";
const int   BACKEND_PORT = 8000;
const char* BACKEND_PATH = "/api/camera/esp32/upload";

// ============================================================
// 2. CẤU HÌNH PHẦN CỨNG (SERVO & IR SENSOR)
// ============================================================
const int SERVO_PIN     = 14;
const int IR_PIN        = 13;
const int SERVO_CLOSE   = 0;
const int SERVO_OPEN    = 90;
const int GATE_OPEN_MS  = 10000; // Thời gian mở cổng (10 giây)

// ============================================================
// 3. CẤU HÌNH CAMERA ESP32-CAM
// ============================================================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ============================================================
// 4. BIẾN TRẠNG THÁI HỆ THỐNG
// ============================================================
Servo      gateServo;
WebServer  server(80);

bool     isCarPresent      = false;
bool     isGateOpen        = false;
unsigned long gateOpenedAt = 0;

unsigned long lastIrChange = 0;
const int     IR_DEBOUNCE_MS = 500;

int cameraFailCount = 0;
const int MAX_CAMERA_FAILS = 5;
bool isWifiReconnecting = false;
const int AUTO_PUSH_RETRY_COUNT = 3;
const int AUTO_PUSH_RETRY_DELAY_MS = 300;

// Latest frame cache để endpoint /latest có thể trả ảnh cho GUI
uint8_t* latestFrameBuf = nullptr;
size_t latestFrameLen = 0;
unsigned long latestFrameAt = 0;
uint32_t latestFrameSeq = 0;

void clearLatestFrame() {
  if (latestFrameBuf != nullptr) {
    free(latestFrameBuf);
    latestFrameBuf = nullptr;
    latestFrameLen = 0;
  }
}

bool cacheLatestFrame(camera_fb_t* fb) {
  if (!fb || !fb->buf || fb->len == 0) return false;

  uint8_t* newBuf = (uint8_t*)ps_malloc(fb->len);
  if (!newBuf) {
    Serial.println("❌ Không đủ RAM để cache ảnh latest.");
    return false;
  }

  memcpy(newBuf, fb->buf, fb->len);
  clearLatestFrame();
  latestFrameBuf = newBuf;
  latestFrameLen = fb->len;
  latestFrameAt = millis();
  latestFrameSeq++;
  return true;
}

// ============================================================
// 5. HÀM KHỞI ĐỘNG CAMERA
// ============================================================
bool setupCamera() {
  camera_config_t config;
  config.ledc_channel  = LEDC_CHANNEL_0;
  config.ledc_timer    = LEDC_TIMER_0;
  config.pin_d0        = Y2_GPIO_NUM;
  config.pin_d1        = Y3_GPIO_NUM;
  config.pin_d2        = Y4_GPIO_NUM;
  config.pin_d3        = Y5_GPIO_NUM;
  config.pin_d4        = Y6_GPIO_NUM;
  config.pin_d5        = Y7_GPIO_NUM;
  config.pin_d6        = Y8_GPIO_NUM;
  config.pin_d7        = Y9_GPIO_NUM;
  config.pin_xclk      = XCLK_GPIO_NUM;
  config.pin_pclk      = PCLK_GPIO_NUM;
  config.pin_vsync     = VSYNC_GPIO_NUM;
  config.pin_href      = HREF_GPIO_NUM;
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
  config.pin_sccb_sda  = SIOD_GPIO_NUM;
  config.pin_sccb_scl  = SIOC_GPIO_NUM;
#else
  config.pin_sscb_sda  = SIOD_GPIO_NUM;
  config.pin_sscb_scl  = SIOC_GPIO_NUM;
#endif
  config.pin_pwdn      = PWDN_GPIO_NUM;
  config.pin_reset     = RESET_GPIO_NUM;
  config.xclk_freq_hz  = 10000000;
  config.pixel_format  = PIXFORMAT_JPEG;
  config.frame_size    = FRAMESIZE_VGA;
  config.jpeg_quality  = 12;
  config.fb_count      = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Camera lỗi: 0x%x\n", err);
    return false;
  }
  Serial.println("✅ Camera sẵn sàng!");
  return true;
}

// ============================================================
// 6. HÀM ĐIỀU KHIỂN CỔNG SERVO
// ============================================================
void openGate() {
  if (isGateOpen) return;
  Serial.println("🔓 Mở cổng (Servo quay 90 độ)...");
  gateServo.write(SERVO_OPEN);
  gateOpenedAt = millis();
  isGateOpen   = true;
}

void closeGate() {
  if (!isGateOpen) return;
  Serial.println("🔒 Đóng cổng (Servo về 0 độ).");
  gateServo.write(SERVO_CLOSE);
  isGateOpen = false;
}

// ============================================================
// 7. HÀM GỬI ẢNH LÊN FASTAPI VÀ ĐỌC KẾT QUẢ AI
// ============================================================
bool uploadImage(camera_fb_t* fb, bool* authorizedOut = nullptr) {
  if (!fb) return false;
  if (authorizedOut) *authorizedOut = false;
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi mất kết nối, bỏ qua upload.");
    return false;
  }

  HTTPClient http;
  String url = "http://" + String(BACKEND_HOST) + ":" + String(BACKEND_PORT) + BACKEND_PATH;
  http.begin(url);
  http.setTimeout(20000); 
  http.addHeader("Content-Type", "image/jpeg");

  int httpCode = http.POST(fb->buf, fb->len);
  bool authorized = false;
  bool uploaded = false;
  
  if (httpCode > 0) {
    String resp = http.getString();
    Serial.printf("📡 Phản hồi từ FastAPI (HTTP %d): %s\n", httpCode, resp.c_str());
    
    // Endpoint mới có thể chỉ trả {"ok":true} hoặc legacy {"authorized":true}
    if (httpCode == 200 && (resp.indexOf("\"authorized\": true") >= 0 || resp.indexOf("\"authorized\":true") >= 0)) {
        authorized = true;
    }

    // Nếu backend chỉ dùng endpoint upload frame thì vẫn coi upload thành công.
    if (httpCode >= 200 && httpCode < 300 && (resp.indexOf("\"ok\":true") >= 0 || resp.indexOf("\"ok\": true") >= 0)) {
      uploaded = true;
      Serial.println("✅ Upload frame thành công.");
    }

    if (httpCode >= 200 && httpCode < 300 && authorized) {
      uploaded = true;
    }
  } else {
    Serial.printf("❌ Gửi ảnh thất bại: %s\n", http.errorToString(httpCode).c_str());
  }
  http.end();

  if (authorizedOut) *authorizedOut = authorized;
  return uploaded;
}

bool autoPushFrameWithRetry(camera_fb_t* fb, bool* authorizedOut = nullptr) {
  if (authorizedOut) *authorizedOut = false;
  if (!fb) return false;

  for (int attempt = 1; attempt <= AUTO_PUSH_RETRY_COUNT; attempt++) {
    bool authorized = false;
    bool uploaded = uploadImage(fb, &authorized);
    if (uploaded) {
      if (authorizedOut) *authorizedOut = authorized;
      if (attempt > 1) {
        Serial.printf("✅ Auto-push thành công ở lần thử %d.\n", attempt);
      }
      return true;
    }

    if (attempt < AUTO_PUSH_RETRY_COUNT) {
      Serial.printf("⚠️ Auto-push thất bại, thử lại lần %d...\n", attempt + 1);
      delay(AUTO_PUSH_RETRY_DELAY_MS);
    }
  }

  Serial.println("❌ Auto-push thất bại sau tất cả lần thử.");
  return false;
}

// ============================================================
// 8. API SERVER NỘI BỘ (TEST THỦ CÔNG)
// ============================================================
void setupWebServer() {
  server.on("/", HTTP_GET, []() {
    server.send(200, "application/json", "{\"status\":\"ok\",\"device\":\"ESP32_Parking_Node_v2.5\"}");
  });

  server.on("/status", HTTP_GET, []() {
    String json = "{";
    json += "\"wifi_rssi\":" + String(WiFi.RSSI()) + ",";
    json += "\"gate_open\":" + String(isGateOpen ? "true" : "false") + ",";
    json += "\"car_present\":" + String(isCarPresent ? "true" : "false") + ",";
    json += "\"free_heap\":" + String(ESP.getFreeHeap()) + ",";
    json += "\"latest_frame_seq\":" + String(latestFrameSeq) + ",";
    json += "\"latest_frame_age_ms\":" + String(latestFrameAt == 0 ? 0 : (millis() - latestFrameAt)) + ",";
    json += "\"ip\":\"" + WiFi.localIP().toString() + "\"";
    json += "}";
    server.send(200, "application/json", json);
  });

  server.on("/latest", HTTP_GET, []() {
    if (latestFrameBuf == nullptr || latestFrameLen == 0) {
      server.send(404, "text/plain", "No latest frame");
      return;
    }
    // Tránh cache ở client/proxy để luôn lấy đúng ảnh mới nhất theo tín hiệu IR.
    server.sendHeader("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
    server.sendHeader("Pragma", "no-cache");
    server.sendHeader("Expires", "0");
    server.sendHeader("X-Frame-Seq", String(latestFrameSeq));
    server.sendHeader("X-Frame-Age-Ms", String(millis() - latestFrameAt));
    server.send_P(200, "image/jpeg", (const char*)latestFrameBuf, latestFrameLen);
  });

  server.on("/open", HTTP_GET, []() {
    openGate();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Da mo cong thu cong\"}");
  });

  server.on("/capture", HTTP_GET, []() {
    Serial.println("\n🌐 [WEB] Lệnh ép chụp ảnh thủ công từ trình duyệt...");
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      server.send(500, "application/json", "{\"status\":\"error\",\"message\":\"Loi camera\"}");
      return;
    }

    cacheLatestFrame(fb);

    bool allowed = false;
    bool uploaded = false;
    if (WiFi.status() == WL_CONNECTED) {
      uploaded = autoPushFrameWithRetry(fb, &allowed);
    }
    esp_camera_fb_return(fb);

    if (allowed) {
      openGate();
      server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"HOP LE -> Da mo cong\"}");
    } else if (uploaded) {
      server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Da auto-push anh, cho ket qua xac thuc\"}");
    } else {
      server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"KHONG HOP LE hoac loi mang\"}");
    }
  });

  server.begin();
  Serial.println("🌐 API Server nội bộ khởi động!");
}

// ============================================================
// 9. SETUP HỆ THỐNG
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // TẮT BẢO VỆ SỤT ÁP (Fix lỗi Brownout)
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  Serial.println("\n===== ESP32 PARKING GATE v2.5 (FINAL) =====");

  // Khởi động Servo
  ESP32PWM::allocateTimer(1);
  gateServo.setPeriodHertz(50);
  gateServo.attach(SERVO_PIN, 500, 2400);
  gateServo.write(SERVO_CLOSE);
  Serial.printf("✅ Servo gắn vào GPIO%d\n", SERVO_PIN);

  // Khởi động cảm biến hồng ngoại
  pinMode(IR_PIN, INPUT_PULLUP);
  Serial.printf("✅ IR sensor gắn vào GPIO%d\n", IR_PIN);

  // Khởi động Camera
  if (!setupCamera()) {
    Serial.println("⛔ Lỗi phần cứng camera, dừng hệ thống.");
    while (true) delay(1000);
  }

  // Kết nối WiFi
  Serial.printf("📶 Kết nối WiFi: %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.printf("\n✅ WiFi OK! IP: %s\n", WiFi.localIP().toString().c_str());

  // Bật WebServer
  setupWebServer();

  // Chụp một frame ban đầu để endpoint /latest có dữ liệu ngay khi boot.
  camera_fb_t* warmup = esp_camera_fb_get();
  if (warmup) {
    cacheLatestFrame(warmup);
    esp_camera_fb_return(warmup);
  }

  Serial.println("=========================================\n");
}

// ============================================================
// 10. VÒNG LẶP CHÍNH (LOOP)
// ============================================================
void loop() {
  server.handleClient();

  // Tự động đóng cổng sau 10 giây
  if (isGateOpen && (millis() - gateOpenedAt >= GATE_OPEN_MS)) {
    closeGate();
  }

  // Đọc tín hiệu IR sensor chống nhiễu
  int irValue = digitalRead(IR_PIN);
  unsigned long now = millis();

  if (now - lastIrChange < IR_DEBOUNCE_MS) {
    delay(10);
    return;
  }

  // XE ĐẾN (IR mức LOW)
  if (irValue == LOW && !isCarPresent) {
    lastIrChange  = now;
    isCarPresent  = true;
    Serial.println("\n🚗 TÍN HIỆU TỪ CẢM BIẾN - Đang chụp ảnh...");

    camera_fb_t* fb = esp_camera_fb_get();
    if (fb) {
      cacheLatestFrame(fb);
      if (WiFi.status() == WL_CONNECTED) {
        bool allowed = false;
        bool uploaded = autoPushFrameWithRetry(fb, &allowed);
        if (allowed) {
          Serial.println("✅ SERVER BÁO HỢP LỆ → Mở cổng!");
          openGate();
        } else if (uploaded) {
          Serial.println("✅ Đã auto-push ảnh thành công lên backend.");
        } else {
          Serial.println("⛔ Auto-push lỗi hoặc backend không phản hồi.");
        }
      } else {
        Serial.println("⚠️ Rớt mạng WiFi, không thể gửi ảnh.");
      }
      esp_camera_fb_return(fb); // Giải phóng RAM ngay
    } else {
      Serial.println("❌ Chụp ảnh thất bại!");
    }
  }
  // XE ĐI (IR mức HIGH)
  else if (irValue == HIGH && isCarPresent) {
    lastIrChange = now;
    isCarPresent = false;
    Serial.println("🚙 Đã rời đi - Chờ xe tiếp theo.\n");
  }

  delay(20);
}