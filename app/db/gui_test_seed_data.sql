/*
Purpose:
- Seed minimal test data for GUI/backend integration checks.
- Cover 4 groups: accounts, vehicles, transfers, parking in/out time.

Target DB:
- school_parking_management (SQL Server)
*/

SET NOCOUNT ON;

/* ----------------------------------------------------------------------
   1) Ensure required columns exist for current backend
---------------------------------------------------------------------- */
IF COL_LENGTH('users', 'balance') IS NULL
BEGIN
    ALTER TABLE users ADD balance FLOAT NOT NULL DEFAULT(50000);
END;

IF COL_LENGTH('vehicles', 'color') IS NULL
BEGIN
    ALTER TABLE vehicles ADD color NVARCHAR(50) NULL;
END;

IF COL_LENGTH('vehicles', 'is_locked') IS NULL
BEGIN
    ALTER TABLE vehicles ADD is_locked BIT NOT NULL DEFAULT(0);
END;

IF COL_LENGTH('vehicles', 'lock_reason') IS NULL
BEGIN
    ALTER TABLE vehicles ADD lock_reason NVARCHAR(255) NULL;
END;

IF COL_LENGTH('transactions', 'lane') IS NULL
BEGIN
    ALTER TABLE transactions ADD lane NVARCHAR(20) NULL;
END;

IF COL_LENGTH('transactions', 'barcode_raw') IS NULL
BEGIN
    ALTER TABLE transactions ADD barcode_raw NVARCHAR(MAX) NULL;
END;

IF COL_LENGTH('transactions', 'scanned_plate') IS NULL
BEGIN
    ALTER TABLE transactions ADD scanned_plate NVARCHAR(30) NULL;
END;

IF COL_LENGTH('transactions', 'entry_iot_image_path') IS NULL
BEGIN
    ALTER TABLE transactions ADD entry_iot_image_path NVARCHAR(255) NULL;
END;

IF COL_LENGTH('transactions', 'exit_iot_image_path') IS NULL
BEGIN
    ALTER TABLE transactions ADD exit_iot_image_path NVARCHAR(255) NULL;
END;

IF COL_LENGTH('transactions', 'entry_local_image_path') IS NULL
BEGIN
    ALTER TABLE transactions ADD entry_local_image_path NVARCHAR(255) NULL;
END;

IF COL_LENGTH('transactions', 'exit_local_image_path') IS NULL
BEGIN
    ALTER TABLE transactions ADD exit_local_image_path NVARCHAR(255) NULL;
END;

IF COL_LENGTH('transactions', 'image_similarity_score') IS NULL
BEGIN
    ALTER TABLE transactions ADD image_similarity_score FLOAT NOT NULL DEFAULT(0);
END;

IF COL_LENGTH('transactions', 'alert_flag') IS NULL
BEGIN
    ALTER TABLE transactions ADD alert_flag BIT NOT NULL DEFAULT(0);
END;

/* ----------------------------------------------------------------------
   2) Create transfer table (wallet/account transfer history)
---------------------------------------------------------------------- */
IF OBJECT_ID('dbo.wallet_transfers', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.wallet_transfers (
        id INT IDENTITY(1,1) PRIMARY KEY,
        transfer_code NVARCHAR(50) NOT NULL UNIQUE,
        account_id INT NOT NULL,
        direction NVARCHAR(20) NOT NULL,
        amount FLOAT NOT NULL,
        balance_before FLOAT NOT NULL,
        balance_after FLOAT NOT NULL,
        note NVARCHAR(255) NULL,
        transaction_id INT NULL,
        created_at DATETIME NOT NULL DEFAULT(GETDATE()),
        CONSTRAINT CK_wallet_transfers_direction CHECK (direction IN ('TOPUP', 'DEBIT', 'REFUND')),
        CONSTRAINT CK_wallet_transfers_amount CHECK (amount > 0),
        CONSTRAINT FK_wallet_transfers_users FOREIGN KEY (account_id) REFERENCES users(id),
        CONSTRAINT FK_wallet_transfers_transactions FOREIGN KEY (transaction_id) REFERENCES transactions(id)
    );
END;

/* ----------------------------------------------------------------------
   3) Seed account data (users)
---------------------------------------------------------------------- */
IF NOT EXISTS (SELECT 1 FROM users WHERE identity_card = 'TEST-STUDENT-001')
BEGIN
    INSERT INTO users (full_name, role, identity_card, phone_number, balance)
    VALUES ('Test Student One', 'Student', 'TEST-STUDENT-001', '0900000001', 150000);
END;

IF NOT EXISTS (SELECT 1 FROM users WHERE identity_card = 'TEST-STUDENT-002')
BEGIN
    INSERT INTO users (full_name, role, identity_card, phone_number, balance)
    VALUES ('Test Student Two', 'Student', 'TEST-STUDENT-002', '0900000002', 95000);
END;

IF NOT EXISTS (SELECT 1 FROM users WHERE identity_card = 'TEST-TEACHER-001')
BEGIN
    INSERT INTO users (full_name, role, identity_card, phone_number, balance)
    VALUES ('Test Teacher One', 'Teacher', 'TEST-TEACHER-001', '0900000003', 210000);
END;

/* ----------------------------------------------------------------------
   4) Seed vehicle data
---------------------------------------------------------------------- */
DECLARE @user_student_1 INT = (SELECT TOP 1 id FROM users WHERE identity_card = 'TEST-STUDENT-001');
DECLARE @user_student_2 INT = (SELECT TOP 1 id FROM users WHERE identity_card = 'TEST-STUDENT-002');
DECLARE @user_teacher_1 INT = (SELECT TOP 1 id FROM users WHERE identity_card = 'TEST-TEACHER-001');

IF @user_student_1 IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM vehicles WHERE license_plate = '59A1-123.45')
BEGIN
    INSERT INTO vehicles (license_plate, vehicle_type, color, is_locked, lock_reason, owner_id)
    VALUES ('59A1-123.45', 'Motorbike', 'Black', 0, NULL, @user_student_1);
END;

IF @user_student_2 IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM vehicles WHERE license_plate = '51B2-678.90')
BEGIN
    INSERT INTO vehicles (license_plate, vehicle_type, color, is_locked, lock_reason, owner_id)
    VALUES ('51B2-678.90', 'Motorbike', 'Red', 0, NULL, @user_student_2);
END;

IF @user_teacher_1 IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM vehicles WHERE license_plate = '30F-256.58')
BEGIN
    INSERT INTO vehicles (license_plate, vehicle_type, color, is_locked, lock_reason, owner_id)
    VALUES ('30F-256.58', 'Car', 'White', 0, NULL, @user_teacher_1);
END;

/* ----------------------------------------------------------------------
   5) Seed parking in/out transactions
---------------------------------------------------------------------- */
DECLARE @vehicle_1 INT = (SELECT TOP 1 id FROM vehicles WHERE license_plate = '59A1-123.45');
DECLARE @vehicle_2 INT = (SELECT TOP 1 id FROM vehicles WHERE license_plate = '51B2-678.90');
DECLARE @vehicle_3 INT = (SELECT TOP 1 id FROM vehicles WHERE license_plate = '30F-256.58');

/* Active parked session for dashboard active list */
IF @vehicle_1 IS NOT NULL
   AND NOT EXISTS (
        SELECT 1
        FROM transactions
        WHERE barcode_raw = 'TEST-QR-0001' AND status = 'Parked' AND time_out IS NULL
   )
BEGIN
    INSERT INTO transactions (
        vehicle_id,
        time_in,
        time_out,
        status,
        fee,
        lane,
        barcode_raw,
        scanned_plate,
        image_similarity_score,
        alert_flag
    )
    VALUES (
        @vehicle_1,
        DATEADD(MINUTE, -35, GETDATE()),
        NULL,
        'Parked',
        0,
        'A',
        'TEST-QR-0001',
        '59A112345',
        0,
        0
    );
END;

/* Completed session for history list */
IF @vehicle_2 IS NOT NULL
   AND NOT EXISTS (
        SELECT 1
        FROM transactions
        WHERE barcode_raw = 'TEST-QR-0002' AND status = 'Completed'
   )
BEGIN
    INSERT INTO transactions (
        vehicle_id,
        time_in,
        time_out,
        status,
        fee,
        lane,
        barcode_raw,
        scanned_plate,
        image_similarity_score,
        alert_flag
    )
    VALUES (
        @vehicle_2,
        DATEADD(HOUR, -6, GETDATE()),
        DATEADD(HOUR, -4, GETDATE()),
        'Completed',
        5000,
        'B',
        'TEST-QR-0002',
        '51B267890',
        86.5,
        0
    );
END;

/* Completed session with higher fee */
IF @vehicle_3 IS NOT NULL
   AND NOT EXISTS (
        SELECT 1
        FROM transactions
        WHERE barcode_raw = 'TEST-QR-0003' AND status = 'Completed'
   )
BEGIN
    INSERT INTO transactions (
        vehicle_id,
        time_in,
        time_out,
        status,
        fee,
        lane,
        barcode_raw,
        scanned_plate,
        image_similarity_score,
        alert_flag
    )
    VALUES (
        @vehicle_3,
        DATEADD(HOUR, -10, GETDATE()),
        DATEADD(HOUR, -2, GETDATE()),
        'Completed',
        18000,
        'C',
        'TEST-QR-0003',
        '30F25658',
        91.2,
        0
    );
END;

/* ----------------------------------------------------------------------
   6) Seed transfer records linked to accounts and parking transactions
---------------------------------------------------------------------- */
DECLARE @tx_2 INT = (
    SELECT TOP 1 id
    FROM transactions
    WHERE barcode_raw = 'TEST-QR-0002'
    ORDER BY id DESC
);

DECLARE @tx_3 INT = (
    SELECT TOP 1 id
    FROM transactions
    WHERE barcode_raw = 'TEST-QR-0003'
    ORDER BY id DESC
);

IF @user_student_1 IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM wallet_transfers WHERE transfer_code = 'WF-TEST-0001')
BEGIN
    INSERT INTO wallet_transfers (
        transfer_code,
        account_id,
        direction,
        amount,
        balance_before,
        balance_after,
        note,
        transaction_id
    )
    VALUES (
        'WF-TEST-0001',
        @user_student_1,
        'TOPUP',
        50000,
        100000,
        150000,
        'Topup by test script',
        NULL
    );
END;

IF @user_student_2 IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM wallet_transfers WHERE transfer_code = 'WF-TEST-0002')
BEGIN
    INSERT INTO wallet_transfers (
        transfer_code,
        account_id,
        direction,
        amount,
        balance_before,
        balance_after,
        note,
        transaction_id
    )
    VALUES (
        'WF-TEST-0002',
        @user_student_2,
        'DEBIT',
        5000,
        100000,
        95000,
        'Parking fee debit',
        @tx_2
    );
END;

IF @user_teacher_1 IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM wallet_transfers WHERE transfer_code = 'WF-TEST-0003')
BEGIN
    INSERT INTO wallet_transfers (
        transfer_code,
        account_id,
        direction,
        amount,
        balance_before,
        balance_after,
        note,
        transaction_id
    )
    VALUES (
        'WF-TEST-0003',
        @user_teacher_1,
        'DEBIT',
        18000,
        228000,
        210000,
        'Car parking fee debit',
        @tx_3
    );
END;

/* ----------------------------------------------------------------------
   7) Quick checks for GUI/backend verification
---------------------------------------------------------------------- */
SELECT TOP 20
    u.id,
    u.full_name,
    u.role,
    u.identity_card,
    u.balance
FROM users u
WHERE u.identity_card LIKE 'TEST-%'
ORDER BY u.id DESC;

SELECT TOP 20
    v.id,
    v.license_plate,
    v.vehicle_type,
    v.color,
    v.owner_id,
    v.is_locked
FROM vehicles v
WHERE v.license_plate IN ('59A1-123.45', '51B2-678.90', '30F-256.58')
ORDER BY v.id DESC;

SELECT TOP 20
    t.id,
    t.vehicle_id,
    t.time_in,
    t.time_out,
    t.status,
    t.fee,
    t.lane,
    t.barcode_raw,
    t.scanned_plate,
    t.image_similarity_score
FROM transactions t
WHERE t.barcode_raw IN ('TEST-QR-0001', 'TEST-QR-0002', 'TEST-QR-0003')
ORDER BY t.id DESC;

SELECT TOP 20
    wt.id,
    wt.transfer_code,
    wt.account_id,
    wt.direction,
    wt.amount,
    wt.balance_before,
    wt.balance_after,
    wt.transaction_id,
    wt.created_at
FROM wallet_transfers wt
WHERE wt.transfer_code LIKE 'WF-TEST-%'
ORDER BY wt.id DESC;
