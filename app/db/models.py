from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Text
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

    email: Optional[str] = Field(default=None, index=True, unique=True)

    clerk_user_id: str = Field(index=True, unique=True)

    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    auth: Optional["UserYouTubeAuth"] = Relationship(back_populates="user")
    channels: List["Channel"] = Relationship(back_populates="user")


# 🔐 OAuth Tokens (1 per user)
class UserYouTubeAuth(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, unique=True)

    access_token: str
    refresh_token: str
    expiry: Optional[datetime]
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    user: Optional[User] = Relationship(back_populates="auth")

# 📺 Channel
class Channel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    youtube_channel_id: str = Field(index=True, unique=True)
    channel_name: str
    description: Optional[str] = Field(default=None, sa_column=Column(Text))

    persona: Optional[str] = Field(default=None, sa_column=Column(Text))
    tone: Optional[str]
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    user: Optional[User] = Relationship(back_populates="channels")
    videos: List["Video"] = Relationship(back_populates="channel")

# 🎥 Video
class Video(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    channel_id: int = Field(foreign_key="channel.id", index=True)

    youtube_video_id: str = Field(index=True, unique=True)
    title: str
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Transcripts can be massive, must be Text
    transcript: Optional[str] = Field(default=None, sa_column=Column(Text)) 
    tags: Optional[str]
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    channel: Optional[Channel] = Relationship(back_populates="videos")
    comments: List["Comment"] = Relationship(back_populates="video")


# 💬 Comment
class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    video_id: int = Field(foreign_key="video.id", index=True)

    youtube_comment_id: str = Field(index=True, unique=True)
    
    # Comments can be long, enforce Text
    comment_text: str = Field(sa_column=Column(Text))
    parent_comment_id: Optional[str] = Field(default=None, index=True)

    author: Optional[str]
    author_channel_id: Optional[str] = Field(default=None, index=True) # to check unique id of comment
    is_creator: bool = False  # for filtering non-creator comments
    intent: Optional[str]
    spam_flag: bool = False
    
    # RAG Queue Flag: True if the AI has already read/replied to this
    is_processed: bool = False 
    
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    video: Optional[Video] = Relationship(back_populates="comments")
    bot_replies: List["Reply"] = Relationship(back_populates="comment")


# 🤖 Reply (Given by bot)
class Reply(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    comment_id: int = Field(foreign_key="comment.id", index=True)

    generated_reply: str = Field(sa_column=Column(Text))
    edited_reply: Optional[str] = Field(default=None, sa_column=Column(Text))
    model_name: Optional[str] = None
    prompt_hash: Optional[str] = Field(default=None, index=True)
    source_chunk_ids: Optional[str] = Field(default=None, sa_column=Column(Text))

    status: ReplyStatus = Field(default=ReplyStatus.pending)
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    comment: Optional[Comment] = Relationship(back_populates="bot_replies")


class RAGChunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    video_id: int = Field(foreign_key="video.id", index=True)

    chunk_hash: str = Field(index=True, unique=True)
    chunk_index: int
    source_type: str = Field(index=True)
    source_ref: Optional[str] = Field(default=None, index=True)
    text: str = Field(sa_column=Column(Text))
    metadata_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_stale: bool = False
    created_at: datetime = Field(default_factory=utc_now)