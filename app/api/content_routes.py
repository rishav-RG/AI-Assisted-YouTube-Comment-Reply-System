from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlmodel import Session, select

from app.crud.comment import upsert_comment
from app.db.models import Channel, Comment, Reply, ReplyStatus, UserYouTubeAuth, Video
from app.db.session import get_session
from app.services.rag_cache import RAGCache
from app.youtube.client import get_youtube_client
from app.youtube.comments import fetch_comments_with_replies, post_reply

router = APIRouter(prefix="/content", tags=["content"])


class PostReplyRequest(BaseModel):
    reply_text: Optional[str] = Field(
        default=None,
        description="Optional override text. If omitted, the latest generated reply is used.",
    )
    prefer_edited_reply: bool = Field(
        default=True,
        description="Use edited_reply first when the latest generated reply has an edited value.",
    )


def _serialize_reply(reply: Optional[Reply]) -> Optional[dict]:
    if not reply:
        return None

    return {
        "id": reply.id,
        "status": reply.status,
        "generated_reply": reply.generated_reply,
        "edited_reply": reply.edited_reply,
        "created_at": reply.created_at,
    }


def _build_latest_reply_map(session: Session, user_id: int, comment_ids: List[int]) -> Dict[int, Reply]:
    if not comment_ids:
        return {}

    replies = session.exec(
        select(Reply)
        .where(Reply.user_id == user_id, Reply.comment_id.in_(comment_ids))
        .order_by(desc(Reply.created_at))
    ).all()

    latest_map: Dict[int, Reply] = {}
    for reply in replies:
        latest_map.setdefault(reply.comment_id, reply)

    return latest_map


def _serialize_comment(comment: Comment, latest_reply: Optional[Reply], include_children: bool = True) -> dict:
    return {
        "id": comment.id,
        "youtube_comment_id": comment.youtube_comment_id,
        "parent_comment_id": comment.parent_comment_id,
        "video_id": comment.video_id,
        "author": comment.author,
        "comment_text": comment.comment_text,
        "intent": comment.intent,
        "spam_flag": comment.spam_flag,
        "is_creator": comment.is_creator,
        "is_processed": comment.is_processed,
        "created_at": comment.created_at,
        "can_generate_reply": not comment.is_creator,
        "latest_reply": _serialize_reply(latest_reply),
        "replies": [] if include_children else None,
    }


@router.get("/overview")
def get_content_overview(session: Session = Depends(get_session)):
    user_id = 1

    channel = session.exec(
        select(Channel)
        .where(Channel.user_id == user_id)
        .order_by(desc(Channel.created_at))
    ).first()

    if not channel:
        return {
            "channel": None,
            "stats": {
                "video_count": 0,
                "comment_count": 0,
                "pending_comment_count": 0,
                "processed_comment_count": 0,
            },
            "videos": [],
        }

    videos = session.exec(
        select(Video)
        .where(Video.user_id == user_id)
        .order_by(desc(Video.created_at))
    ).all()

    video_ids = [video.id for video in videos if video.id is not None]
    comments = []
    if video_ids:
        comments = session.exec(
            select(Comment)
            .where(Comment.user_id == user_id, Comment.video_id.in_(video_ids))
        ).all()

    comments_by_video: Dict[int, List[Comment]] = defaultdict(list)
    for comment in comments:
        comments_by_video[comment.video_id].append(comment)

    video_payload = []
    total_pending = 0
    total_processed = 0

    for video in videos:
        related_comments = comments_by_video.get(video.id, [])
        pending_count = sum(
            1
            for item in related_comments
            if not item.is_creator and not item.is_processed
        )
        processed_count = sum(
            1 for item in related_comments if item.is_processed
        )
        creator_count = sum(1 for item in related_comments if item.is_creator)

        total_pending += pending_count
        total_processed += processed_count

        video_payload.append(
            {
                "id": video.id,
                "youtube_video_id": video.youtube_video_id,
                "title": video.title,
                "description": video.description,
                "created_at": video.created_at,
                "comment_count": len(related_comments),
                "pending_comment_count": pending_count,
                "processed_comment_count": processed_count,
                "creator_comment_count": creator_count,
            }
        )

    return {
        "channel": {
            "id": channel.id,
            "youtube_channel_id": channel.youtube_channel_id,
            "channel_name": channel.channel_name,
            "description": channel.description,
            "persona": channel.persona,
            "tone": channel.tone,
            "created_at": channel.created_at,
        },
        "stats": {
            "video_count": len(videos),
            "comment_count": len(comments),
            "pending_comment_count": total_pending,
            "processed_comment_count": total_processed,
        },
        "videos": video_payload,
    }


@router.get("/videos/{video_id}")
def get_video_detail(video_id: int, session: Session = Depends(get_session)):
    user_id = 1

    video = session.get(Video, video_id)
    if not video or video.user_id != user_id:
        raise HTTPException(status_code=404, detail="Video not found")

    channel = session.get(Channel, video.channel_id)

    comments = session.exec(
        select(Comment)
        .where(Comment.user_id == user_id, Comment.video_id == video_id)
        .order_by(desc(Comment.created_at))
    ).all()

    latest_reply_map = _build_latest_reply_map(
        session=session,
        user_id=user_id,
        comment_ids=[comment.id for comment in comments if comment.id is not None],
    )

    replies_by_parent: Dict[str, List[Comment]] = defaultdict(list)
    top_level_comments: List[Comment] = []

    for comment in comments:
        if comment.parent_comment_id:
            replies_by_parent[comment.parent_comment_id].append(comment)
        else:
            top_level_comments.append(comment)

    for parent_id in replies_by_parent:
        replies_by_parent[parent_id].sort(key=lambda item: item.created_at)

    threads = []
    known_parent_ids = {comment.youtube_comment_id for comment in top_level_comments}

    for comment in top_level_comments:
        comment_payload = _serialize_comment(comment, latest_reply_map.get(comment.id))
        thread_replies = []
        for reply in replies_by_parent.get(comment.youtube_comment_id, []):
            thread_replies.append(
                _serialize_comment(
                    reply,
                    latest_reply_map.get(reply.id),
                    include_children=False,
                )
            )
        comment_payload["replies"] = thread_replies
        threads.append(comment_payload)

    orphan_replies = []
    for comment in comments:
        if comment.parent_comment_id and comment.parent_comment_id not in known_parent_ids:
            orphan_replies.append(
                _serialize_comment(comment, latest_reply_map.get(comment.id), include_children=False)
            )

    return {
        "channel": {
            "id": channel.id if channel else None,
            "youtube_channel_id": channel.youtube_channel_id if channel else None,
            "channel_name": channel.channel_name if channel else None,
        },
        "video": {
            "id": video.id,
            "youtube_video_id": video.youtube_video_id,
            "title": video.title,
            "description": video.description,
            "transcript": video.transcript,
            "created_at": video.created_at,
        },
        "stats": {
            "total_comments": len(comments),
            "top_level_comments": len(top_level_comments),
            "reply_comments": sum(1 for item in comments if item.parent_comment_id),
            "pending_comment_count": sum(
                1
                for item in comments
                if not item.is_creator and not item.is_processed
            ),
            "processed_comment_count": sum(1 for item in comments if item.is_processed),
        },
        "threads": threads,
        "orphan_replies": orphan_replies,
    }


@router.post("/videos/{video_id}/sync-comments")
async def sync_video_comments(video_id: int, session: Session = Depends(get_session)):
    user_id = 1

    video = session.get(Video, video_id)
    if not video or video.user_id != user_id:
        raise HTTPException(status_code=404, detail="Video not found")

    channel = session.get(Channel, video.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found for this video")

    user_auth = session.exec(
        select(UserYouTubeAuth).where(UserYouTubeAuth.user_id == user_id)
    ).first()
    if not user_auth:
        raise HTTPException(status_code=400, detail="No YouTube auth found for user")

    try:
        youtube = await get_youtube_client(user_auth, session)
        latest_comments = fetch_comments_with_replies(youtube, video.youtube_video_id)

        existing_comments = session.exec(
            select(Comment).where(Comment.user_id == user_id, Comment.video_id == video_id)
        ).all()
        existing_ids = {item.youtube_comment_id for item in existing_comments}

        inserted = 0
        updated = 0

        for item in latest_comments:
            comment_id = item.get("youtube_comment_id")
            if comment_id in existing_ids:
                updated += 1
            else:
                inserted += 1
                existing_ids.add(comment_id)

            upsert_comment(
                session=session,
                user_id=user_id,
                video_id=video_id,
                channel_youtube_id=channel.youtube_channel_id,
                data=item,
            )

        cache = RAGCache()
        cache.delete_prefix("aggregate", f"{user_id}:{video_id}")
        cache.delete_prefix("retrieval", f"{user_id}:{video_id}:")

        refreshed_total = session.exec(
            select(Comment).where(Comment.user_id == user_id, Comment.video_id == video_id)
        ).all()

        return {
            "status": "ok",
            "video_id": video_id,
            "youtube_video_id": video.youtube_video_id,
            "inserted": inserted,
            "updated": updated,
            "fetched": len(latest_comments),
            "total_comments": len(refreshed_total),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/comments/{comment_id}/post-reply")
async def post_reply_for_comment(
    comment_id: int,
    payload: PostReplyRequest,
    session: Session = Depends(get_session),
):
    user_id = 1

    comment = session.get(Comment, comment_id)
    if not comment or comment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.is_creator:
        raise HTTPException(status_code=400, detail="Cannot post reply to creator comment")

    video = session.get(Video, comment.video_id)
    if not video or video.user_id != user_id:
        raise HTTPException(status_code=404, detail="Video not found for comment")

    channel = session.get(Channel, video.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found for comment")

    user_auth = session.exec(
        select(UserYouTubeAuth).where(UserYouTubeAuth.user_id == user_id)
    ).first()
    if not user_auth:
        raise HTTPException(status_code=400, detail="No YouTube auth found for user")

    latest_generated_reply = session.exec(
        select(Reply)
        .where(Reply.user_id == user_id, Reply.comment_id == comment_id)
        .order_by(desc(Reply.created_at))
    ).first()

    submitted_reply = (payload.reply_text or "").strip()
    if submitted_reply:
        reply_text = submitted_reply
    elif latest_generated_reply:
        candidate = (
            latest_generated_reply.edited_reply
            if payload.prefer_edited_reply and latest_generated_reply.edited_reply
            else latest_generated_reply.generated_reply
        )
        reply_text = (candidate or "").strip()
    else:
        raise HTTPException(status_code=404, detail="No generated reply found for this comment")

    if not reply_text:
        raise HTTPException(status_code=400, detail="Reply text cannot be empty")

    parent_id = comment.parent_comment_id or comment.youtube_comment_id

    try:
        youtube = await get_youtube_client(user_auth, session)
        posted = post_reply(youtube=youtube, parent_id=parent_id, text=reply_text)

        if not posted.get("youtube_comment_id"):
            raise HTTPException(status_code=502, detail="YouTube did not return the posted comment ID")

        posted_author_channel_id = posted.get("author_channel_id") or channel.youtube_channel_id

        saved_reply_comment = upsert_comment(
            session=session,
            user_id=user_id,
            video_id=video.id,
            channel_youtube_id=channel.youtube_channel_id,
            data={
                "youtube_comment_id": posted["youtube_comment_id"],
                "comment_text": posted.get("comment_text") or reply_text,
                "author": posted.get("author") or channel.channel_name,
                "author_channel_id": posted_author_channel_id,
                "parent_comment_id": parent_id,
            },
        )

        if latest_generated_reply:
            latest_generated_reply.status = ReplyStatus.approved
            if submitted_reply:
                latest_generated_reply.edited_reply = submitted_reply
            session.add(latest_generated_reply)

        comment.is_processed = True
        session.add(comment)
        session.commit()

        return {
            "status": "posted",
            "comment_id": comment_id,
            "youtube_parent_comment_id": parent_id,
            "youtube_reply_comment_id": posted["youtube_comment_id"],
            "reply_text": posted.get("comment_text") or reply_text,
            "saved_reply_comment_id": saved_reply_comment.id,
            "reply_record_id": latest_generated_reply.id if latest_generated_reply else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
