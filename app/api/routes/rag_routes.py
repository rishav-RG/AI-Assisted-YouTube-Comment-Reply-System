from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db.models import Comment
from app.db.session import get_session
from app.api.deps import get_current_user
from app.db.models import User
from app.services.comment_labeling_pipeline import CommentLabelingPipeline
from app.services.hf_inference_client import HFInferenceError
from app.services.rag_reply_service import RAGReplyService

router = APIRouter(prefix="/rag", tags=["rag"])


class GenerateOptions(BaseModel):
    """Options for RAG generation."""

    force_regenerate: bool = Field(
        default=False,
        description="If true, forces regeneration even if a recent reply exists.",
    )
    top_k: Optional[int] = Field(
        default=None,
        description="Number of context chunks to retrieve. Defaults to the system setting.",
    )


@router.post("/generate/video/{video_id}")
async def generate_for_video(
    video_id: int,
    payload: GenerateOptions,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # user_id = 1

    user_id = current_user.id # now using current user id instead hardcoded
    pipeline = CommentLabelingPipeline()
    service = RAGReplyService()

    try:
        await pipeline.run_full_pipeline(
            session=session,
            user_id=user_id,
            video_id=video_id,
        )

        summary = service.generate_for_video(
            session=session,
            user_id=user_id,
            video_id=video_id,
            force_regenerate=payload.force_regenerate,
            top_k=payload.top_k,
        )
        session.commit()
        return {"status": "ok", "summary": summary}
    except HFInferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/generate/comment/{comment_id}")
async def generate_for_comment(
    comment_id: int,
    payload: GenerateOptions,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # user_id = 1
    
    user_id = current_user.id # now using current user id instead hardcoded
    pipeline = CommentLabelingPipeline()
    service = RAGReplyService()

    try:
        comment = session.get(Comment, comment_id)
        if not comment or comment.user_id != user_id:
            raise ValueError("Comment not found")

        await pipeline.run_full_pipeline(
            session=session,
            user_id=user_id,
            video_id=comment.video_id,
        )

        result = service.generate_for_comment(
            session=session,
            user_id=user_id,
            comment_id=comment_id,
            force_regenerate=payload.force_regenerate,
            top_k=payload.top_k,
        )
        session.commit()
        return {"status": "ok", "result": result}
    except HFInferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    