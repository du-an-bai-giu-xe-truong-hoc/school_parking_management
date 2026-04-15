import urllib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Cấu hình gốc
DB_CONFIG = { 
    'DRIVER': '{ODBC Driver 17 for SQL Server}', 
    'SERVER': 'localhost', 
    'DATABASE': 'school_parking_management', 
    'UID': 'sa', 
    'PWD': '1' 
}

params = urllib.parse.quote_plus(
    f"DRIVER={DB_CONFIG['DRIVER']};"
    f"SERVER={DB_CONFIG['SERVER']};"
    f"DATABASE={DB_CONFIG['DATABASE']};"
    f"UID={DB_CONFIG['UID']};"
    f"PWD={DB_CONFIG['PWD']};"
)
SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc:///?odbc_connect={params}"

# Khởi tạo Engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True
)

# Chỉ dùng sessionmaker cho FastAPI (không dùng scoped_session của Flask nữa)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Trạm cấp phát Session cho FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()