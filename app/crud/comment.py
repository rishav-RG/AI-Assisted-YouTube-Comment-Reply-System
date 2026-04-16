# upsert comments + link to video

from sqlmodel import Session, select
from app.db.models import Comment


def upsert_comment(
    session: Session,
    user_id: int,
    video_id: int,
    channel_youtube_id: str,
    data: dict,
    commit: bool = True,
    refresh: bool = True,
):
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
        existing.author = data.get("author")
        existing.parent_comment_id = data.get("parent_comment_id")
        existing.is_creator = is_creator
        if text_changed:
            existing.is_processed = False
        session.add(existing)
        if commit:
            session.commit()
            if refresh:
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
    if commit:
        session.commit()
        if refresh:
            session.refresh(comment)
    else:
        session.flush()

    return comment


def upsert_comments_batch(
    session: Session,
    user_id: int,
    video_id: int,
    channel_youtube_id: str,
    comments: list[dict],
    commit: bool = False,
):
    if not comments:
        return

    comment_ids = list(
        {
            item["youtube_comment_id"]
            for item in comments
            if item.get("youtube_comment_id")
        }
    )

    if not comment_ids:
        return

    existing_comments = session.exec(
        select(Comment).where(
            Comment.user_id == user_id,
            Comment.youtube_comment_id.in_(comment_ids),
        )
    ).all()
    existing_map = {
        item.youtube_comment_id: item for item in existing_comments
    }

    new_comments = []

    for item in comments:
        youtube_comment_id = item.get("youtube_comment_id")
        if not youtube_comment_id:
            continue

        comment_author_id = item.get("author_channel_id")
        is_creator = comment_author_id == channel_youtube_id
        existing = existing_map.get(youtube_comment_id)

        if existing:
            text_changed = existing.comment_text != item["comment_text"]
            existing.comment_text = item["comment_text"]
            existing.author = item.get("author")
            existing.author_channel_id = comment_author_id
            existing.parent_comment_id = item.get("parent_comment_id")
            existing.is_creator = is_creator
            if text_changed:
                existing.is_processed = False
            session.add(existing)
            continue

        new_comments.append(
            Comment(
                user_id=user_id,
                video_id=video_id,
                youtube_comment_id=youtube_comment_id,
                parent_comment_id=item.get("parent_comment_id"),
                comment_text=item["comment_text"],
                author=item.get("author"),
                author_channel_id=comment_author_id,
                is_creator=is_creator,
            )
        )

    if new_comments:
        session.add_all(new_comments)

    if commit:
        session.commit()
    else:
        session.flush()

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
        # Keep spam_flag aligned with the latest model label.
        comment.spam_flag = intent.lower() == "spam"
        session.add(comment)
        session.commit()
        session.refresh(comment)
    
    return comment