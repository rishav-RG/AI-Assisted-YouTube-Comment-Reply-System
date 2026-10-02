from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.services.comment_labeling_pipeline import CommentLabelingPipeline
from app.services.hf_inference_client import HFInferenceError
from app.services.youtube_sync import sync_youtube
from app.services.rag_reply_service import RAGReplyService
from app.api.deps import get_current_user
from app.db.models import User

router = APIRouter()


@router.post("/youtube/sync")
async def run_sync(
    run_rag: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # user_id = 1 # just for testing it is being hardcoded but in future this should be replaced by user_id and which should come from authentication of our application
    # user would signin/singup to our application so we have some user_id for it, we have to use that here
    # For that we have to add an authentication system (JWT/session)

    user_id = current_user.id # now using current user id instead hardcoded

    user_id = current_user.id # now using current user id instead hardcoded

    try:
        synced_video_ids = await sync_youtube(user_id, session)

        pipeline = CommentLabelingPipeline()
        labeling_summaries = []
        labeled_total = 0
        for video_id in synced_video_ids:
            if video_id is None:
                continue
            result = await pipeline.run_full_pipeline(
                session=session,
                user_id=user_id,
                video_id=video_id,
            )
            labeled_count = int(result.get("labeled_count", 0))
            labeled_total += labeled_count
            labeling_summaries.append(
                {
                    "video_id": video_id,
                    "labeled_count": labeled_count,
                    "status": result.get("status", "unknown"),
                }
            )

        if not run_rag:
            return {
                "status": "synced",
                "videos": synced_video_ids,
                "labeling": {
                    "total_labeled": labeled_total,
                    "videos": labeling_summaries,
                },
            }

        service = RAGReplyService()
        summaries = []
        for video_id in synced_video_ids:
            if video_id is None:
                continue
            summaries.append(
                service.generate_for_video(
                    session=session,
                    user_id=user_id,
                    video_id=video_id,
                    force_regenerate=False,
                )
            )

        session.commit()

        return {
            "status": "synced_and_generated",
            "videos": synced_video_ids,
            "labeling": {
                "total_labeled": labeled_total,
                "videos": labeling_summaries,
            },
            "rag": summaries,
        }
    except HFInferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
