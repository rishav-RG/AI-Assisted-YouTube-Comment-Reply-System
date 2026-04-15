# This is backend api service of our application
# This file defines routes to connect Youtube for a user (not multiple user allowed yet)

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone

from app.youtube.oauth import get_oauth_url, exchange_code_for_tokens
from app.db.session import get_session
from app.db.models import UserYouTubeAuth

router = APIRouter()

@router.get("/auth/youtube")
def connect_youtube():
    return RedirectResponse(get_oauth_url())


@router.get("/auth/callback")
async def oauth_callback(code: str, session: Session = Depends(get_session)):
    token_data = await exchange_code_for_tokens(code)

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token") # these token may not exist that'why accessed with .get() method
    expires_in = token_data.get("expires_in", 3600) # these token may not exist that'why accessed with .get() method

    expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    user_id = 1 # just for testing it is being hardcoded but in future this should be replaced by user_id and which should come from authentication of our application\
    # user would signin/singup to our application so we have some user_id for it, we have to use that here
    # For that we have to add an authentication system (JWT/session)

    existing = session.exec(
        select(UserYouTubeAuth).where(UserYouTubeAuth.user_id == user_id)
    ).first()

    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token or existing.refresh_token
        existing.expiry = expiry
        session.add(existing)
    else:
        session.add(
            UserYouTubeAuth(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expiry=expiry
            )
        )

    session.commit()

    return {"status": "connected"}