import psycopg2
import io
import importlib
import qrcode
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Setup paths
ROOT_DIR = Path(__file__).resolve().parent.parent
QR_DIR = ROOT_DIR / "qr_codes"
BARCODE_DIR = ROOT_DIR / "barcodes"
QR_DIR.mkdir(parents=True, exist_ok=True)
BARCODE_DIR.mkdir(parents=True, exist_ok=True)

def get_database_url():
    import os
    url = os.getenv("DATABASE_URL")
    if url: return url
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    return "postgresql://postgres:yourpassword@localhost:5432/school_parking_management"

def get_data():
    conn = psycopg2.connect("postgresql://postgres:abc@localhost:5432/school_parking_management")
    cur = conn.cursor()
    # Fetch Student + RFID + Vehicle
    query = """
        SELECT s.MaSV, s.HoTen, r.MaRFID, x.BienSo
        FROM SinhVien s
        LEFT JOIN TheRFID r ON s.MaSV = r.MaSV
        LEFT JOIN Xe x ON s.MaSV = x.MaSV
    """
    cur.execute(query)
    data = cur.fetchall()
    conn.close()
    return data

def build_code128_barcode(text):
    barcode_module = importlib.import_module("barcode")
    barcode_writer_module = importlib.import_module("barcode.writer")
    code128_cls = getattr(barcode_module, "Code128")
    image_writer_cls = getattr(barcode_writer_module, "ImageWriter")
    
    code = code128_cls(text, writer=image_writer_cls())
    buffer = io.BytesIO()
    code.write(
        buffer,
        options={
            "module_width": 0.34,
            "module_height": 26,
            "quiet_zone": 6.0,
            "write_text": False,
            "dpi": 300,
        },
    )
    buffer.seek(0)
    with Image.open(buffer) as barcode_image:
        return barcode_image.convert("RGB")

def _safe_filename(value: str) -> str:
    allowed = []
    for char in value:
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        elif char.isspace():
            allowed.append("_")
    normalized = "".join(allowed).strip("_")
    return normalized or "student"

def generate_barcode(masv, hoten, bien_so):
    if not bien_so:
        return
    barcode_image = build_code128_barcode(bien_so)
    barcode_image = barcode_image.resize((520, 190), Image.Resampling.LANCZOS)

    card = Image.new("RGB", (560, 380), color=(250, 250, 250))
    card.paste(barcode_image, (20, 18))

    draw = ImageDraw.Draw(card)
    label_font = ImageFont.load_default()
    
    draw.text((max(20, (card.width - len(bien_so)*10) // 2), 218), bien_so, fill=(15, 15, 15))
    draw.text((20, 285), f"MaSV: {masv}", fill=(20, 20, 20), font=label_font)
    draw.text((20, 325), f"BienSo: {bien_so}", fill=(20, 20, 20), font=label_font)
    draw.text((20, 345), hoten, fill=(20, 20, 20), font=label_font)

    filename = f"{masv}_{_safe_filename(hoten)}_barcode.png"
    output_path = BARCODE_DIR / filename
    card.save(output_path)

def generate_qr(masv, hoten, ma_rfid):
    if not ma_rfid:
        return
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(ma_rfid)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_image = qr_image.resize((320, 320), Image.Resampling.LANCZOS)

    card = Image.new("RGB", (420, 440), color=(250, 250, 250))
    card.paste(qr_image, (50, 20))

    draw = ImageDraw.Draw(card)
    font = ImageFont.load_default()
    draw.text((40, 360), f"MaSV: {masv}", fill=(20, 20, 20), font=font)
    draw.text((40, 380), f"RFID: {ma_rfid}", fill=(20, 20, 20), font=font)
    draw.text((40, 400), hoten, fill=(20, 20, 20), font=font)

    filename = f"{masv}_{_safe_filename(hoten)}.png"
    output_path = QR_DIR / filename
    card.save(output_path)

if __name__ == "__main__":
    records = get_data()
    for row in records:
        masv, hoten, ma_rfid, bien_so = row
        generate_qr(masv, hoten, ma_rfid)
        generate_barcode(masv, hoten, bien_so)
    print(f"Done generating codes for {len(records)} records.")
