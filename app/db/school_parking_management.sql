CREATE DATABASE school_parking_management;
-- -------------------------------------------------------------------------
-- BẢNG 1: users (Hồ sơ Chủ phương tiện / Người dùng)
-- -------------------------------------------------------------------------
CREATE TABLE users (
    id INT IDENTITY (1, 1) PRIMARY KEY,
    full_name NVARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL, -- Chức vụ: 'Student', 'Teacher', 'Staff'
    identity_card VARCHAR(20) NOT NULL UNIQUE, -- CCCD hoặc Mã SV (để đối chiếu)
    phone_number VARCHAR(15),
    created_at DATETIME DEFAULT GETDATE ()
);

-- -------------------------------------------------------------------------
-- BẢNG 2: vehicles (Hồ sơ Phương tiện)
-- -------------------------------------------------------------------------
CREATE TABLE vehicles (
    id INT IDENTITY (1, 1) PRIMARY KEY,
    license_plate VARCHAR(20) NOT NULL UNIQUE, -- Biển số xe (Dữ liệu quan trọng nhất cho OCR)
    vehicle_type VARCHAR(50) NOT NULL, -- Phân loại: 'Motorbike', 'Bicycle', 'Car'
    color NVARCHAR(50),
    owner_id INT NOT NULL,
    -- Thiết lập liên kết ngoại (Foreign Key) về bảng users
    -- CASCADE: Nếu xóa người dùng, toàn bộ xe của người đó cũng bị xóa khỏi hồ sơ
    CONSTRAINT FK_Vehicle_User FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE
);

-- -------------------------------------------------------------------------
-- BẢNG 3: transactions (Hồ sơ Lượt gửi xe ra/vào)
-- -------------------------------------------------------------------------
CREATE TABLE transactions (
    id INT IDENTITY (1, 1) PRIMARY KEY,
    vehicle_id INT NOT NULL,
    time_in DATETIME DEFAULT GETDATE () NOT NULL, -- Mặc định là thời điểm camera quét được xe vào
    time_out DATETIME NULL, -- Chờ cập nhật khi xe ra khỏi bãi
    status VARCHAR(20) DEFAULT 'Parked', -- Trạng thái: 'Parked' (Đang đỗ), 'Completed' (Đã rời đi)
    fee FLOAT DEFAULT 0.0,
    -- Thiết lập liên kết ngoại về bảng vehicles
    CONSTRAINT FK_Transaction_Vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles (id) ON DELETE CASCADE
);
-- -------------------------------------------------------------------------
-- 1. NẠP HỒ SƠ NGƯỜI DÙNG (20 Đối tượng)
-- -------------------------------------------------------------------------
INSERT INTO
    users (
        full_name,
        role,
        identity_card,
        phone_number
    )
VALUES (
        'Nguyen Van An',
        'Student',
        '311021001',
        '0901111222'
    ),
    (
        'Tran Thi Binh',
        'Student',
        '311021002',
        '0902222333'
    ),
    (
        'Le Hoang Cuong',
        'Student',
        '311021003',
        '0903333444'
    ),
    (
        'Pham My Dung',
        'Student',
        '311021004',
        '0904444555'
    ),
    (
        'Vu Truong Giang',
        'Student',
        '311021005',
        '0905555666'
    ),
    (
        'Hoang Thi Hoa',
        'Student',
        '311021006',
        '0906666777'
    ),
    (
        'Ngo Kien Huy',
        'Student',
        '311021007',
        '0907777888'
    ),
    (
        'Bui Ngoc Hai',
        'Student',
        '311021008',
        '0908888999'
    ),
    (
        'Doan Minh Khoa',
        'Student',
        '311021009',
        '0909999000'
    ),
    (
        'Ly Nhan Tong',
        'Student',
        '311021010',
        '0911222333'
    ),
    (
        'Truong Vo Ky',
        'Student',
        '311021011',
        '0912333444'
    ),
    (
        'Mai Phuong Thuy',
        'Student',
        '311021012',
        '0913444555'
    ),
    (
        'Chau Tinh Tri',
        'Student',
        '311021013',
        '0914555666'
    ),
    (
        'Ton That Thuyet',
        'Student',
        '311021014',
        '0915666777'
    ),
    (
        'Huynh Dac Bao',
        'Student',
        '311021015',
        '0916777888'
    ),
    (
        'Nguyen Quang Hai',
        'Staff',
        '048099000111',
        '0981111222'
    ),
    (
        'Le Thi Tuoi',
        'Staff',
        '048099000222',
        '0982222333'
    ),
    (
        'Nguyen Xuan Loc',
        'Staff',
        '048099000333',
        '0983333444'
    ),
    (
        'Hoang Tra My',
        'Teacher',
        '048099000444',
        '0991111222'
    ),
    (
        'Le Nguyen Tra My',
        'Teacher',
        '048099000555',
        '0992222333'
    );

-- -------------------------------------------------------------------------
-- 2. NẠP HỒ SƠ PHƯƠNG TIỆN (20 Phương tiện, liên kết với id 1-20)
-- -------------------------------------------------------------------------
INSERT INTO
    vehicles (
        license_plate,
        vehicle_type,
        color,
        owner_id
    )
VALUES (
        '43A1-123.45',
        'Motorbike',
        'Black',
        1
    ),
    (
        '43B2-987.65',
        'Motorbike',
        'Red',
        2
    ),
    (
        '43C1-555.22',
        'Motorbike',
        'White',
        3
    ),
    (
        '92D1-333.44',
        'Motorbike',
        'Blue',
        4
    ),
    (
        '92E1-111.99',
        'Motorbike',
        'Silver',
        5
    ),
    (
        '43F1-222.88',
        'Motorbike',
        'Black',
        6
    ),
    (
        '43G1-444.77',
        'Motorbike',
        'Red',
        7
    ),
    (
        '75H1-666.55',
        'Motorbike',
        'White',
        8
    ),
    (
        '43K1-888.33',
        'Motorbike',
        'Green',
        9
    ),
    (
        '43L1-999.11',
        'Motorbike',
        'Yellow',
        10
    ),
    (
        '43M1-101.01',
        'Motorbike',
        'Black',
        11
    ),
    (
        '43N1-202.02',
        'Motorbike',
        'Red',
        12
    ),
    (
        '43P1-303.03',
        'Motorbike',
        'White',
        13
    ),
    (
        '92Q1-404.04',
        'Motorbike',
        'Blue',
        14
    ),
    (
        '43R1-505.05',
        'Motorbike',
        'Silver',
        15
    ),
    (
        '43S1-606.06',
        'Motorbike',
        'Black',
        16
    ),
    (
        '43T1-707.07',
        'Motorbike',
        'White',
        17
    ),
    (
        '43U1-808.08',
        'Bicycle',
        'Red',
        18
    ),
    (
        '43A-909.09',
        'Car',
        'Black',
        19
    ),
    (
        '43A-123.99',
        'Car',
        'White',
        20
    );