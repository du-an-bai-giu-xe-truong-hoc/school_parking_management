import os
import tempfile
import warnings

warnings.filterwarnings(
    "ignore",
    message=r"You are using a Python version .* end of life.*",
    category=FutureWarning,
)

from app.services.fuzzy_matcher import (
    chuan_hoa_bien_so,
    gui_ve_main_controller,
    kiem_tra_xe_hop_le,
    khoi_tao_db_mau,
)


def test_chuan_hoa_bien_so():
    assert chuan_hoa_bien_so("43F1 - 123.45") == "43F112345"
    assert chuan_hoa_bien_so(" 29a-999.99 ") == "29A99999"
    assert chuan_hoa_bien_so(None) == ""


def test_kiem_tra_xe_hop_le_with_sample_db():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "parking.db")
        khoi_tao_db_mau(db_path=db_path)

        result_ok = kiem_tra_xe_hop_le("43F1 123.4S", threshold=80, db_path=db_path)
        assert result_ok["hople"] is True
        assert result_ok["bien_so"] == "43F1-123.45"
        assert result_ok["ty_le"] >= 80

        result_no = kiem_tra_xe_hop_le("43F1 999.99", threshold=80, db_path=db_path)
        assert result_no["hople"] is False


def test_gui_ve_main_controller_calls_receiver():
    captured = {}

    def fake_receiver(ocr_text, ket_qua):
        captured["ocr_text"] = ocr_text
        captured["ket_qua"] = ket_qua
        return {"ok": True}

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "parking.db")
        khoi_tao_db_mau(db_path=db_path)

        result = gui_ve_main_controller(
            ocr_result="43F1 123.4S",
            threshold=80,
            db_path=db_path,
            receiver=fake_receiver,
        )

    assert captured["ocr_text"] == "43F1 123.4S"
    assert captured["ket_qua"]["hople"] is True
    assert result["hople"] is True
