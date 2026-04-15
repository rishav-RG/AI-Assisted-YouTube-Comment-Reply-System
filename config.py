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