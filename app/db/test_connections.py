from sqlalchemy import create_engine, text
import urllib.parse

# Khai báo lại cấu hình tại đây để test độc lập
# Yêu cầu sửa lại tài khoản + mật khẩu cũng như chạy file
# datafile.sql trước khi kiểm thử xem chạy được không?
DB_CONFIG = { 
    'DRIVER': '{ODBC Driver 17 for SQL Server}', 
    'SERVER': 'localhost', 
    'DATABASE': 'school_parking_management', 
    'UID': 'sa', 
    'PWD': '1' 
}
# Vẫn sử dụng SQLAlchemy để kiểm tra máy chủ SQL Server
params = urllib.parse.quote_plus(
    f"DRIVER={DB_CONFIG['DRIVER']};SERVER={DB_CONFIG['SERVER']};DATABASE={DB_CONFIG['DATABASE']};UID={DB_CONFIG['UID']};PWD={DB_CONFIG['PWD']};"
)
SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc:///?odbc_connect={params}"

# Khởi tạo Engine
engine = create_engine(SQLALCHEMY_DATABASE_URI)

def test_db():
    try:
        # Cố gắng mở một kết nối và thực thi một lệnh SQL cơ bản
        with engine.connect() as connection:
            result = connection.execute(text("SELECT @@VERSION"))
            for row in result:
                print("✅ KẾT NỐI THÀNH CÔNG! Phiên bản SQL Server:")
                print(row[0])
    except Exception as e:
        print("❌ KẾT NỐI THẤT BẠI. Chi tiết lỗi:")
        print(e)

if __name__ == "__main__":
    test_db()