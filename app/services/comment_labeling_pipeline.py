import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from app.db.models import Comment 
from sqlmodel import Session

from config import HF_BATCH_SIZE
from app.db.models import Video
from app.crud.comment import update_comment_intent
from app.services.context_aggregator import get_comments_aggregated, get_video_channel_context
from app.services.hf_inference_client import HFInferenceClient, HFInferenceError, hf_client
from app.services.rag_cache import RAGCache
from app.services.rag_reply_service import RAGReplyService

logger = logging.getLogger(__name__)


class CommentLabelingPipeline:
    def __init__(
        self,
        client: HFInferenceClient = hf_client,
        cache: Optional[RAGCache] = None,
    ) -> None:
        self.client = client
        self.cache = cache or RAGCache()

    def _flatten_threads(self, threads: List[dict]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for thread_index, thread in enumerate(threads):
            comment = thread.get("comment", {})
            comment_text = (comment.get("text") or "").strip()
            comment_id = (comment.get("id"))
            if comment_text:
                items.append(
                    {
                        "id": comment_id,
                        "text": comment_text,
                        "thread_index": thread_index,
                        "role": "parent",
                        "is_creator": bool(comment.get("is_creator")),
                    }
                )

            replies = thread.get("replies", [])
            for reply_index, reply in enumerate(replies):
                reply_text = (reply.get("text") or "").strip()
                reply_id = (reply.get("id"))
                if not reply_text:
                    continue
                items.append(
                    {
                        "id" : reply_id,
                        "text": reply_text,
                        "thread_index": thread_index,
                        "reply_index": reply_index,
                        "role": "reply",
                        "is_creator": bool(reply.get("is_creator")),
                    }
                )

        return items
    
    def _from_raw_comments(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for idx, comment in enumerate(comments):
            comment_text = (comment.get("text") or "").strip()
            if not comment_text:
                continue
            items.append({
                "id": comment.get("id", f"comment_{idx}"),  # ← id now carried through
                "text": comment_text,
                "thread_index": idx,
                "role": "comment",
                "is_creator": False,
            })
        return items
        
    def _to_threaded_output(self, labeled_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
     threads: Dict[int, Dict[str, Any]] = {}

     for item in labeled_items:
        thread_index = int(item.get("thread_index", 0))
        thread = threads.setdefault(thread_index, {"comment": None, "replies": []})


        entry = {
            "id": item.get("id"), 
            "text": item.get("text", ""),
            "label": item.get("label", ""),
            "is_creator": bool(item.get("is_creator")),
        }

        role = item.get("role")
        if role in ("parent", "comment"):
            thread["comment"] = entry
        else:
            reply = {
                **entry,
                "reply_index": item.get("reply_index", 0),
            }
            thread["replies"].append(reply)

     ordered = [threads[idx] for idx in sorted(threads)]
     for thread in ordered:
        thread["replies"].sort(key=lambda r: r.get("reply_index", 0))
        for reply in thread["replies"]:
            reply.pop("reply_index", None)
     return ordered

    def _cache_key(self, text: str) -> str:
        return self.cache.stable_hash({"text": text})

    def _build_batches(
        self, texts: List[str], indices: List[int], batch_size: int
    ) -> List[Tuple[List[str], List[int]]]:
        batches: List[Tuple[List[str], List[int]]] = []
        for start in range(0, len(texts), batch_size):
            end = start + batch_size
            batches.append((texts[start:end], indices[start:end]))
        return batches
    
    # this will call fn to update comment intent in db
    def _save_labels_to_db(self, session: Session, user_id: int, labeled_items: List[Dict[str, Any]]):
        for item in labeled_items:
            youtube_comment_id = item.get("id")
            label = item.get("label")
            if youtube_comment_id and label:
                update_comment_intent(session, user_id, youtube_comment_id, label)

    async def _label_texts(self, texts: List[str], use_cache: bool = True) -> List[str]:
        if not texts:
            return []

        labels: List[Optional[str]] = [None] * len(texts)
        to_fetch_texts: List[str] = []
        to_fetch_indices: List[int] = []

        for idx, text in enumerate(texts):
            cached_label = None
            if use_cache:
                cached = self.cache.get_json("hf_label", self._cache_key(text))
                if cached:
                    cached_label = cached.get("label")

            if cached_label is not None:
                labels[idx] = str(cached_label)
            else:
                to_fetch_texts.append(text)
                to_fetch_indices.append(idx)

        if to_fetch_texts:
            logger.info(
                "Labeling %s comments (%s cached, %s uncached)",
                len(texts),
                len(texts) - len(to_fetch_texts),
                len(to_fetch_texts),
            )
            batch_size = max(1, HF_BATCH_SIZE)
            batches = self._build_batches(to_fetch_texts, to_fetch_indices, batch_size)
            semaphore = asyncio.Semaphore(max(1, self.client.max_concurrency))

            async def run_batch(batch_texts: List[str], batch_indices: List[int]) -> None:
                async with semaphore:
                    logger.debug("HF batch size %s", len(batch_texts))
                    batch_labels = await self.client.predict_batch(batch_texts)

                if len(batch_labels) != len(batch_texts):
                    raise HFInferenceError(
                        "HF inference response length mismatch",
                    )

                for offset, label in enumerate(batch_labels):
                    idx = batch_indices[offset]
                    labels[idx] = str(label)
                    if use_cache:
                        self.cache.set_json(
                            "hf_label",
                            self._cache_key(texts[idx]),
                            {"label": str(label)},
                        )

            await asyncio.gather(
                *[run_batch(batch_texts, batch_indices) for batch_texts, batch_indices in batches]
            )

        if any(label is None for label in labels):
            raise HFInferenceError("HF inference returned incomplete labels")

        return [label for label in labels if label is not None]

    async def label_comment_items(
        self, items: List[Dict[str, Any]], use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        texts = [item.get("text", "") for item in items]
        labels = await self._label_texts(texts, use_cache=use_cache)

        labeled_items: List[Dict[str, Any]] = []
        for idx, item in enumerate(items):
            labeled_items.append({**item, "label": labels[idx]})

        return labeled_items

    async def run_full_pipeline(
        self,
        session: Session,
        user_id: int,
        comments: Optional[List[str]] = None,
        video_id: Optional[int] = None,
    ) -> Dict[str, Any]:

        items: List[Dict[str, Any]] = []
        if comments:
            items = self._from_raw_comments(comments)
        elif video_id is not None:
            video = session.get(Video, video_id)
            if not video or video.user_id != user_id:
                raise ValueError("Video not found")
            threads = get_comments_aggregated(video)
            items = self._flatten_threads(threads)
        else:
            raise ValueError("Either comments or video_id must be provided")

        if not items:
            return {"labeled_count": 0, "status": "no_comments_found"}
        
        # Label the items using the ML model
        labeled_items = await self.label_comment_items(items)

        # calling fn to save labels to DB
        if video_id is not None:
            self._save_labels_to_db(session, user_id, labeled_items)

        return {
            "labeled_count": len(labeled_items),
            "status": "success",
        }