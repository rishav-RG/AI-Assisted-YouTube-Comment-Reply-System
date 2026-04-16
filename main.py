import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from contextlib import asynccontextmanager
from app.db.init_db import init_db
from app.db.errors import is_transient_db_operational_error
from app.api.oauth_routes import router as oauth_router
from app.api.sync_routes import router as sync_router
from app.api.rag_routes import router as rag_router
from app.api.predict_routes import router as predict_router
from app.api.content_routes import router as content_router
from app.services.hf_inference_client import hf_client
import asyncio

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting app...")
    # start up logic
    await asyncio.to_thread(init_db)
    yield
    # shutting down logic
    await hf_client.close()
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

app.include_router(oauth_router)
app.include_router(sync_router)
app.include_router(rag_router)
app.include_router(predict_router)
app.include_router(content_router)


@app.exception_handler(OperationalError)
async def handle_operational_error(request: Request, exc: OperationalError):
    if is_transient_db_operational_error(exc):
        logger.warning(
            "Transient DB error on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=503,
            content={"detail": "Database temporarily unavailable. Please retry."},
        )

    logger.exception(
        "Operational DB error on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Database operation failed."},
    )

@app.get("/")
def root():
    return {"message": "API running"}