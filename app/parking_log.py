import psycopg2
from datetime import datetime
from typing import Optional, Tuple

DATABASE_URL = "postgresql://postgres:abc@localhost:5432/school_parking_management"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def log_parking_event(ma_rfid: str, bien_so: str) -> Tuple[str, str]:
    """
    Logs the parking event.
    Returns a tuple: (action, timestamp_str)
    action: "ENTRY" or "EXIT"
    """
    # Prefer ma_rfid for tracking, fallback to bien_so
    identifier_col = "MaRFID" if ma_rfid else "BienSo"
    identifier_val = ma_rfid if ma_rfid else bien_so
    
    if not identifier_val:
        return "ERROR", "No valid ID provided"

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. Check if there is an active parking session
                cur.execute(f"""
                    SELECT id 
                    FROM LichSuVaoRa 
                    WHERE {identifier_col} = %s AND TrangThai = 'Đang đỗ'
                    ORDER BY ThoiGianVao DESC LIMIT 1
                """, (identifier_val,))
                
                record = cur.fetchone()
                now = datetime.now()
                time_str = now.strftime("%Y-%m-%d %H:%M:%S")
                
                if record:
                    # Vehicle is currently parked -> THIS IS AN EXIT
                    ma_gd = record[0]
                    cur.execute("""
                        UPDATE LichSuVaoRa
                        SET ThoiGianRa = %s, TrangThai = 'Đã ra'
                        WHERE id = %s
                    """, (now, ma_gd))
                    conn.commit()
                    return "EXIT", time_str
                else:
                    # Vehicle is not parked -> THIS IS AN ENTRY
                    # Insert both MaRFID and BienSo if available
                    cur.execute("""
                        INSERT INTO LichSuVaoRa (MaRFID, BienSo, ThoiGianVao, TrangThai)
                        VALUES (%s, %s, %s, 'Đang đỗ')
                    """, (ma_rfid or None, bien_so or None, now))
                    conn.commit()
                    return "ENTRY", time_str
    except Exception as e:
        print(f"Database error in log_parking_event: {e}")
        return "ERROR", str(e)
