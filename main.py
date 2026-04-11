from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.init_db import init_db
from app.api.oauth_routes import router as oauth_router
from app.api.sync_routes import router as sync_router
from app.api.rag_routes import router as rag_router
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting app...")
    # start up logic
    await asyncio.to_thread(init_db)
    yield
    # shutting down logic
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

app.include_router(oauth_router)
app.include_router(sync_router)
app.include_router(rag_router)

@app.get("/")
def root():
    return {"message": "API running"}