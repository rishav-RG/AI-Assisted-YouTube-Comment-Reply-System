# upsert videos + link to channel

from sqlmodel import Session, select
from app.db.models import Video


def upsert_video(
    session: Session,
    user_id: int,
    channel_id: int,
    data: dict,
    commit: bool = True,
    refresh: bool = True,
):
    existing = session.exec(
        select(Video).where(
            Video.youtube_video_id == data["youtube_video_id"],
            Video.user_id == user_id
        )
    ).first()

    if existing:
        existing.title = data["title"]
        existing.description = data["description"]
        session.add(existing)
        if commit:
            session.commit()
            if refresh:
                session.refresh(existing)
        return existing

    video = Video(
        user_id=user_id,
        channel_id=channel_id,
        youtube_video_id=data["youtube_video_id"],
        title=data["title"],
        description=data["description"]
    )

    session.add(video)
    if commit:
        session.commit()
        if refresh:
            session.refresh(video)
    else:
        session.flush()

    return video