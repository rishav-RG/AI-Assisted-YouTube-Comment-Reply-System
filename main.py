from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.init_db import init_db
from app.api.routes.oauth_routes import router as oauth_router
from app.api.routes.sync_routes import router as sync_router
from app.api.routes.rag_routes import router as rag_router
from app.api.routes.predict_routes import router as predict_router
from app.api.routes.content_routes import router as content_router
from app.api.routes.clerk_routes import router as clerk_router
from app.services.hf_inference_client import hf_client
import asyncio

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
app.include_router(clerk_router)

@app.get("/")
def root():
    return {"message": "API running"}