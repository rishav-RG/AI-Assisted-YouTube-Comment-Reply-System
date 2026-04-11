from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.services.youtube_sync import sync_youtube
from app.services.rag_reply_service import RAGReplyService

router = APIRouter()


@router.post("/youtube/sync")
async def run_sync(
    run_rag: bool = False,
    session: Session = Depends(get_session),
):
    user_id = 1 # just for testing it is being hardcoded but in future this should be replaced by user_id and which should come from authentication of our application
    # user would signin/singup to our application so we have some user_id for it, we have to use that here
    # For that we have to add an authentication system (JWT/session)

    synced_video_ids = await sync_youtube(user_id, session)
    if not run_rag:
        return {"status": "synced", "videos": synced_video_ids}

    service = RAGReplyService()
    summaries = []
    for video_id in synced_video_ids:
        summaries.append(
            service.generate_for_video(
                session=session,
                user_id=user_id,
                video_id=video_id,
                force_regenerate=False,
            )
        )

    return {"status": "synced_and_generated", "videos": synced_video_ids, "rag": summaries}