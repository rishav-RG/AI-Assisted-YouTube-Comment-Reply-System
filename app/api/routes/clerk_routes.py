from fastapi import APIRouter, Request, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import User
import os
from svix.webhooks import Webhook, WebhookVerificationError

router = APIRouter()

@router.post("/webhooks/clerk")
async def clerk_webhook(
    request: Request,
    session: Session = Depends(get_session)
):
    """
    Handle Clerk webhooks (user.created, etc.)
    """

    # 🔹 1. Get raw body (IMPORTANT: do NOT use request.json())
    payload = await request.body()

    # 🔹 2. Extract Svix headers
    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")

    if not svix_id or not svix_timestamp or not svix_signature:
        raise HTTPException(status_code=400, detail="Missing Svix headers")

    headers = {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": svix_signature,
    }

    # 🔹 3. Load webhook secret
    secret = os.getenv("CLERK_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # 🔹 4. Verify webhook using Svix
    wh = Webhook(secret)

    try:
        event = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        print("Webhook verification failed:", str(e))
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 🔹 5. Handle events
    event_type = event.get("type")

    if event_type == "user.created":
        user_data = event["data"]

        email = user_data["email_addresses"][0]["email_address"]
        clerk_user_id = user_data["id"]

        # Check if user already exists
        existing_user = session.exec(
            select(User).where(User.email == email)
        ).first()

        if not existing_user:
            new_user = User(
                email=email,
                clerk_user_id=clerk_user_id  # optional but recommended
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            print(f"User created in DB: {email}")
        else:
            print(f"User already exists: {email}")

    else:
        print(f"Ignored event: {event_type}")

    return {"status": "success"}