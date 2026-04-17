import os
import urllib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


def _build_default_connection_string() -> str:
    driver = os.getenv("DB_DRIVER", "{ODBC Driver 18 for SQL Server}")
    server = os.getenv("DB_SERVER", "localhost")
    port = os.getenv("DB_PORT", "")
    database = os.getenv("DB_DATABASE", "school_parking_management")
    uid = os.getenv("DB_UID", "sa")
    pwd = os.getenv("DB_PWD", "1")
    encrypt = os.getenv("DB_ENCRYPT", "no")
    trust_cert = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")
    login_timeout = os.getenv("DB_LOGIN_TIMEOUT", "30")

    server_with_port = f"{server},{port}" if port else server
    return (
        f"DRIVER={driver};"
        f"SERVER={server_with_port};"
        f"DATABASE={database};"
        f"UID={uid};"
        f"PWD={pwd};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust_cert};"
        f"LoginTimeout={login_timeout};"
    )


def _build_database_uri() -> str:
    explicit_uri = os.getenv("SQLALCHEMY_DATABASE_URI")
    if explicit_uri:
        return explicit_uri

    explicit_odbc = os.getenv("ODBC_CONNECTION_STRING")
    connection_string = explicit_odbc if explicit_odbc else _build_default_connection_string()
    params = urllib.parse.quote_plus(connection_string)
    return f"mssql+pyodbc:///?odbc_connect={params}"


SQLALCHEMY_DATABASE_URI = _build_database_uri()
engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    echo=os.getenv("DB_ECHO", "false").strip().lower() == "true",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()