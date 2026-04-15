# upsert comments + link to video

from sqlmodel import Session, select
from app.db.models import Comment


def upsert_comment(session: Session, user_id: int, video_id: int,channel_youtube_id: str, data: dict):
    existing = session.exec(
        select(Comment).where(
            Comment.youtube_comment_id == data["youtube_comment_id"],
            Comment.user_id == user_id
        )
    ).first()
    
    comment_author_id = data.get("author_channel_id")
    is_creator = (comment_author_id == channel_youtube_id)

    if existing:
        text_changed = existing.comment_text != data["comment_text"]
        existing.comment_text = data["comment_text"]
        existing.author_channel_id = comment_author_id 
        existing.is_creator = is_creator
        if text_changed:
            existing.is_processed = False
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    comment = Comment(
        user_id=user_id,
        video_id=video_id,
        youtube_comment_id=data["youtube_comment_id"],
        parent_comment_id=data.get("parent_comment_id"), # Use .get() for safety
        comment_text=data["comment_text"],
        author=data.get("author"),
        author_channel_id=comment_author_id, 
        is_creator=is_creator
    )

    session.add(comment)
    session.commit()
    session.refresh(comment)

    return comment

# updates comment labels and spam flag in db after getting from ML pipeline
def update_comment_intent(session: Session, user_id: int, youtube_comment_id: str, intent: str) -> Comment | None:
    comment = session.exec(
        select(Comment).where(
            Comment.youtube_comment_id == youtube_comment_id,
            Comment.user_id == user_id
        )
    ).first()

    if comment:
        comment.intent = intent
        if intent.lower() == "spam": # update spam_flag if labeled as "spam"
            comment.spam_flag = True
        session.add(comment)
        session.commit()
        session.refresh(comment)
    
    return comment