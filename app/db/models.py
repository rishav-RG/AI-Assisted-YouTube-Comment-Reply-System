from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from enum import Enum


# 🔥 Common timestamp helper
def utc_now():
    return datetime.now(timezone.utc)


# 🔥 Reply Status Enum
class ReplyStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# 👤 User
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)

    created_at: datetime = Field(default_factory=utc_now)


# 🔐 OAuth Tokens (1 per user)
class UserYouTubeAuth(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, unique=True)

    access_token: str
    refresh_token: str
    expiry: Optional[datetime]

    created_at: datetime = Field(default_factory=utc_now)


# 📺 Channel
class Channel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    youtube_channel_id: str = Field(index=True)
    channel_name: str
    description: Optional[str]

    persona: Optional[str]
    tone: Optional[str]

    created_at: datetime = Field(default_factory=utc_now)


# 🎥 Video
class Video(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    channel_id: int = Field(foreign_key="channel.id", index=True)

    youtube_video_id: str = Field(index=True)
    title: str
    description: Optional[str]
    transcript: Optional[str]
    tags: Optional[str]

    created_at: datetime = Field(default_factory=utc_now)


# 💬 Comment
class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    video_id: int = Field(foreign_key="video.id", index=True)

    youtube_comment_id: str = Field(index=True)
    comment_text: str
    parent_comment_id: Optional[str]

    author: Optional[str]
    intent: Optional[str]
    spam_flag: bool = False

    created_at: datetime = Field(default_factory=utc_now)


# 🤖 Reply (Given by bot)
class Reply(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    comment_id: int = Field(foreign_key="comment.id", index=True)

    generated_reply: str
    edited_reply: Optional[str]

    status: ReplyStatus = Field(default=ReplyStatus.pending)

    created_at: datetime = Field(default_factory=utc_now)