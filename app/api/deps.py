# dependencies like: get_current_user, get_db_session, auth extractors are considered part of the API layer that's why they are putted down into api folder

# for fetching current user

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select

from app.db.session import get_session
from app.db.models import User


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    # Clerk sends this header after auth middleware
    clerk_user_id = request.headers.get("x-clerk-user-id")

    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Missing Clerk user ID")

    user = session.exec(
        select(User).where(User.clerk_user_id == clerk_user_id)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found in DB")

    return user