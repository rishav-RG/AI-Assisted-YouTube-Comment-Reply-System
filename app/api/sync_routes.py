from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.services.youtube_sync import sync_youtube

router = APIRouter()


@router.post("/youtube/sync")
async def run_sync(session: Session = Depends(get_session)):
    user_id = 1 # just for testing it is being hardcoded but in future this should be replaced by user_id and which should come from authentication of our application
    # user would signin/singup to our application so we have some user_id for it, we have to use that here
    # For that we have to add an authentication system (JWT/session)

    await sync_youtube(user_id, session)
    return {"status": "synced"}