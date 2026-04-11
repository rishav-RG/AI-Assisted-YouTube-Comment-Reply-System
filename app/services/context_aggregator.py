from sqlmodel import Session
from app.db.models import Video

def get_comments_aggregated(video: Video) -> list[dict]:
    # 1. Separate top-level comments from replies
    top_level_comments = [c for c in video.comments if not c.parent_comment_id]
    replies = [c for c in video.comments if c.parent_comment_id]

    # 2. Create a dictionary to easily look up replies by their parent's ID
    replies_map: dict[int, list[dict]] = {}
    for reply in replies:
        replies_map.setdefault(reply.parent_comment_id, []).append({
            "text": reply.comment_text,
            "is_creator": reply.is_creator
        })

    # 3. Build the structured list
    structured_comments = []
    for parent in top_level_comments:
        structured_comments.append({
            "comment": {
                "text": parent.comment_text,
                "is_creator": parent.is_creator
            },
            "replies": replies_map.get(parent.youtube_comment_id, [])
        })

    return structured_comments


def get_video_channel_context(video: Video) -> dict:
    return {
        "channel_context": {
            "persona": video.channel.persona if video.channel else "Default persona",
            "tone": video.channel.tone if video.channel else "Default tone"
        },
        "video_context": {
            "title": video.title,
            "description": video.description,
            "transcript": video.transcript
        }
    }


def get_aggregated_context(db: Session, video_id: int) -> dict:
    video = db.get(Video, video_id)
    if not video:
        return {}

    context = get_video_channel_context(video)
    context["comments_context"] = get_comments_aggregated(video)
    return context