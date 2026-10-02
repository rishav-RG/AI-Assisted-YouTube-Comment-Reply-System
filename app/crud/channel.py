# insert/update channel (no duplicates)

from sqlmodel import Session, select
from app.db.models import Channel


def upsert_channel(session: Session, user_id: int, data: dict):
    existing = session.exec(
        select(Channel).where(
            Channel.youtube_channel_id == data["youtube_channel_id"],
            Channel.user_id == user_id
        )
    ).first()

    if existing:
        existing.channel_name = data["channel_name"]
        existing.description = data["description"]
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    channel = Channel(
        user_id=user_id,
        youtube_channel_id=data["youtube_channel_id"],
        channel_name=data["channel_name"],
        description=data["description"]
    )

    session.add(channel)
    session.commit()
    session.refresh(channel)

    return channel