from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlmodel import Session

from app.db.session import get_session
from app.services.comment_labeling_pipeline import CommentLabelingPipeline
from app.services.hf_inference_client import HFInferenceError, hf_client

router = APIRouter(tags=["ml"])


class PredictRequest(BaseModel):
    text: str


class PredictResponse(BaseModel):
    input: str
    label: str


class BatchPredictRequest(BaseModel):
    texts: List[str]


class BatchPredictResponse(BaseModel):
    predictions: List[str]

class CommentItem(BaseModel):
    id: str
    text: str

class FullPipelineRequest(BaseModel):
    comments: Optional[List[CommentItem]] = None
    video_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_input(self):
        if not self.comments and self.video_id is None:
            raise ValueError("Either comments or video_id must be provided")
        return self


class FullPipelineResponse(BaseModel):
    labeled_count: int
    status: str


@router.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest) -> PredictResponse:
    try:
        labels = await hf_client.predict_batch([payload.text])
    except HFInferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not labels:
        raise HTTPException(status_code=502, detail="HF inference returned no labels")

    return PredictResponse(input=payload.text, label=labels[0])


@router.post("/batch_predict", response_model=BatchPredictResponse)
async def batch_predict(payload: BatchPredictRequest) -> BatchPredictResponse:
    if not payload.texts:
        return BatchPredictResponse(predictions=[])

    try:
        labels = await hf_client.predict_batch(payload.texts)
    except HFInferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return BatchPredictResponse(predictions=labels)


@router.post("/full_pipeline", response_model=FullPipelineResponse)
async def full_pipeline(
    payload: FullPipelineRequest,
    session: Session = Depends(get_session),
) -> FullPipelineResponse:
    """
    This endpoint now ONLY handles comment labeling.
    It fetches comments, gets their intent from the ML model,
    and saves the labels to the database.
    """
    user_id = 1 # this must be fixed , must come from auth 
    pipeline = CommentLabelingPipeline()

    try:
        # The 'comments' payload needs to be passed correctly as a list of dicts
        comment_data = [c.model_dump() for c in payload.comments] if payload.comments else None

        result = await pipeline.run_full_pipeline(
            session=session,
            user_id=user_id,    
            comments=comment_data,
            video_id=payload.video_id,
        ) 
        return FullPipelineResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HFInferenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc