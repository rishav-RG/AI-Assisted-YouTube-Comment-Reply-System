import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_CHAT_MODEL = os.getenv("COHERE_CHAT_MODEL", "command-a-03-2025")
COHERE_EMBED_MODEL = os.getenv("COHERE_EMBED_MODEL", "embed-v4.0")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "yt-comment-rag")
PINECONE_NAMESPACE_PREFIX = os.getenv("PINECONE_NAMESPACE_PREFIX", "yt-comrep")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

REDIS_URL = os.getenv("REDIS_URL")
REDIS_CACHE_TTL_SECONDS = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "900"))
SQL_ECHO = os.getenv("SQL_ECHO", "false").strip().lower() in {
	"1",
	"true",
	"yes",
	"on",
}
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT_SECONDS = int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "30"))
DB_POOL_RECYCLE_SECONDS = int(os.getenv("DB_POOL_RECYCLE_SECONDS", "300"))
DB_POOL_USE_LIFO = os.getenv("DB_POOL_USE_LIFO", "true").strip().lower() in {
	"1",
	"true",
	"yes",
	"on",
}
DB_CONNECT_TIMEOUT_SECONDS = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "10"))
DB_KEEPALIVES = os.getenv("DB_KEEPALIVES", "true").strip().lower() in {
	"1",
	"true",
	"yes",
	"on",
}
DB_KEEPALIVES_IDLE_SECONDS = int(os.getenv("DB_KEEPALIVES_IDLE_SECONDS", "30"))
DB_KEEPALIVES_INTERVAL_SECONDS = int(
	os.getenv("DB_KEEPALIVES_INTERVAL_SECONDS", "10")
)
DB_KEEPALIVES_COUNT = int(os.getenv("DB_KEEPALIVES_COUNT", "5"))
DB_OPERATION_MAX_RETRIES = int(os.getenv("DB_OPERATION_MAX_RETRIES", "3"))
DB_OPERATION_RETRY_BACKOFF_SECONDS = float(
	os.getenv("DB_OPERATION_RETRY_BACKOFF_SECONDS", "0.75")
)

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "900"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
RAG_MAX_COMMENTS_CONTEXT = int(os.getenv("RAG_MAX_COMMENTS_CONTEXT", "100"))

HF_INFERENCE_URL = os.getenv(
	"HF_INFERENCE_URL",
	"https://rishavgoyal2004-yt-comment-intent-classifier.hf.space/predict",
)
HF_TIMEOUT_SECONDS = float(os.getenv("HF_TIMEOUT_SECONDS", "25"))
HF_MAX_RETRIES = int(os.getenv("HF_MAX_RETRIES", "2"))
HF_RETRY_BACKOFF_SECONDS = float(os.getenv("HF_RETRY_BACKOFF_SECONDS", "1.0"))
HF_BATCH_SIZE = int(os.getenv("HF_BATCH_SIZE", "32"))
HF_MAX_CONCURRENCY = int(os.getenv("HF_MAX_CONCURRENCY", "4"))