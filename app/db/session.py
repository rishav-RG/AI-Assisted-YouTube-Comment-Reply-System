from sqlmodel import create_engine, Session
from config import DATABASE_URL

# Added pooling arguments for Neon/Serverless stability
engine = create_engine(
    DATABASE_URL, 
    echo=True,
    pool_pre_ping=True,  # Vital: Tests connection before use
    pool_recycle=300,    # Matches Neon's 5-minute idle timeout
    connect_args={"sslmode": "require"} # Ensures secure connection
)

def get_session():
    with Session(engine) as session:
        yield session