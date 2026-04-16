from sqlmodel import create_engine, Session
from config import (
    DATABASE_URL,
    SQL_ECHO,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT_SECONDS,
    DB_POOL_RECYCLE_SECONDS,
    DB_POOL_USE_LIFO,
    DB_CONNECT_TIMEOUT_SECONDS,
    DB_KEEPALIVES,
    DB_KEEPALIVES_IDLE_SECONDS,
    DB_KEEPALIVES_INTERVAL_SECONDS,
    DB_KEEPALIVES_COUNT,
)

# Added pooling arguments for Neon/Serverless stability
engine = create_engine(
    DATABASE_URL, 
    echo=SQL_ECHO,
    pool_pre_ping=True,  # Vital: Tests connection before use
    pool_recycle=DB_POOL_RECYCLE_SECONDS,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT_SECONDS,
    pool_use_lifo=DB_POOL_USE_LIFO,
    connect_args={
        "sslmode": "require",
        "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
        "keepalives": 1 if DB_KEEPALIVES else 0,
        "keepalives_idle": DB_KEEPALIVES_IDLE_SECONDS,
        "keepalives_interval": DB_KEEPALIVES_INTERVAL_SECONDS,
        "keepalives_count": DB_KEEPALIVES_COUNT,
    },
)

def get_session():
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise