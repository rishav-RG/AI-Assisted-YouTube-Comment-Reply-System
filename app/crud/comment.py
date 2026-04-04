# upsert comments + link to video

from sqlmodel import Session, select
from app.db.models import Comment


def upsert_comment(session: Session, user_id: int, video_id: int, data: dict):
    existing = session.exec(
        select(Comment).where(
            Comment.youtube_comment_id == data["youtube_comment_id"],
            Comment.user_id == user_id
        )
    ).first()

    if existing:
        existing.comment_text = data["comment_text"]
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    comment = Comment(
        user_id=user_id,
        video_id=video_id,
        youtube_comment_id=data["youtube_comment_id"],
        parent_comment_id=data["parent_comment_id"],
        comment_text=data["comment_text"],
        author=data.get("author")
    )

    session.add(comment)
    session.commit()
    session.refresh(comment)

    return comment