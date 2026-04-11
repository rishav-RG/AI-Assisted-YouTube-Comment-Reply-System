from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.db.session import get_session
from app.services.rag_reply_service import RAGReplyService

router = APIRouter(prefix="/rag", tags=["rag"])


class GenerateOptions(BaseModel):
    force_regenerate: bool = False
    top_k: Optional[int] = None


@router.post("/generate/video/{video_id}")
def generate_for_video(
    video_id: int,
    payload: GenerateOptions,
    session: Session = Depends(get_session),
):
    user_id = 1
    service = RAGReplyService()

    try:
        summary = service.generate_for_video(
            session=session,
            user_id=user_id,
            video_id=video_id,
            force_regenerate=payload.force_regenerate,
            top_k=payload.top_k,
        )
        return {"status": "ok", "summary": summary}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/generate/comment/{comment_id}")
def generate_for_comment(
    comment_id: int,
    payload: GenerateOptions,
    session: Session = Depends(get_session),
):
    user_id = 1
    service = RAGReplyService()

    try:
        result = service.generate_for_comment(
            session=session,
            user_id=user_id,
            comment_id=comment_id,
            force_regenerate=payload.force_regenerate,
            top_k=payload.top_k,
        )
        return {"status": "ok", "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
