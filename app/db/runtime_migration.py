"""Runtime DB migration helpers for SQL Server environments without Alembic."""

from __future__ import annotations

from sqlalchemy.engine import Engine


def apply_runtime_migrations(engine: Engine) -> None:
    """Add missing columns needed by the security/billing parking workflow."""

    statements = [
        """
        IF COL_LENGTH('users', 'balance') IS NULL
        BEGIN
            ALTER TABLE users ADD balance FLOAT NOT NULL DEFAULT(50000);
        END
        """,
        """
        IF COL_LENGTH('vehicles', 'color') IS NULL
        BEGIN
            ALTER TABLE vehicles ADD color NVARCHAR(50) NULL;
        END
        """,
        """
        IF COL_LENGTH('vehicles', 'is_locked') IS NULL
        BEGIN
            ALTER TABLE vehicles ADD is_locked BIT NOT NULL DEFAULT(0);
        END
        """,
        """
        IF COL_LENGTH('vehicles', 'lock_reason') IS NULL
        BEGIN
            ALTER TABLE vehicles ADD lock_reason NVARCHAR(255) NULL;
        END
        """,
        """
        IF COL_LENGTH('transactions', 'lane') IS NULL
        BEGIN
            ALTER TABLE transactions ADD lane NVARCHAR(20) NULL;
        END
        """,
        """
        IF COL_LENGTH('transactions', 'barcode_raw') IS NULL
        BEGIN
            ALTER TABLE transactions ADD barcode_raw NVARCHAR(MAX) NULL;
        END
        """,
        """
        IF COL_LENGTH('transactions', 'scanned_plate') IS NULL
        BEGIN
            ALTER TABLE transactions ADD scanned_plate NVARCHAR(30) NULL;
        END
        """,
        """
        IF COL_LENGTH('transactions', 'entry_iot_image_path') IS NULL
        BEGIN
            ALTER TABLE transactions ADD entry_iot_image_path NVARCHAR(255) NULL;
        END
        """,
        """
        IF COL_LENGTH('transactions', 'exit_iot_image_path') IS NULL
        BEGIN
            ALTER TABLE transactions ADD exit_iot_image_path NVARCHAR(255) NULL;
        END
        """,
        """
        IF COL_LENGTH('transactions', 'entry_local_image_path') IS NULL
        BEGIN
            ALTER TABLE transactions ADD entry_local_image_path NVARCHAR(255) NULL;
        END
        """,
        """
        IF COL_LENGTH('transactions', 'exit_local_image_path') IS NULL
        BEGIN
            ALTER TABLE transactions ADD exit_local_image_path NVARCHAR(255) NULL;
        END
        """,
        """
        IF COL_LENGTH('transactions', 'image_similarity_score') IS NULL
        BEGIN
            ALTER TABLE transactions ADD image_similarity_score FLOAT NOT NULL DEFAULT(0);
        END
        """,
        """
        IF COL_LENGTH('transactions', 'alert_flag') IS NULL
        BEGIN
            ALTER TABLE transactions ADD alert_flag BIT NOT NULL DEFAULT(0);
        END
        """,
        "UPDATE users SET balance = 50000 WHERE balance IS NULL",
        "UPDATE vehicles SET is_locked = 0 WHERE is_locked IS NULL",
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
