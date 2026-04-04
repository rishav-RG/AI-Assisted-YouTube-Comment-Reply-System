# app/services/context_aggregator.py

from sqlmodel import Session
from app.db.models import Video, Comment

def get_aggregated_context(db: Session, video_id: int) -> dict:
    """
    Aggregates all relevant text context for a given video to be used in a RAG pipeline.

    This function queries the database for a specific video and gathers:
    1.  Channel Context: The pre-defined persona and tone for the channel.
    2.  Video Context: The video's title, description, and full transcript.
    3.  Comments Context: The text from all existing comments on that video,
        structured into parent comments and their corresponding replies.

    Args:
        db (Session): The database session to use for querying.
        video_id (int): The ID of the video to aggregate context for.

    Returns:
        dict: A dictionary containing the structured text context, or an empty
              dictionary if the video is not found.
    """
  
    video = db.get(Video, video_id)

    if not video:
        return {}

    # Channel Context
    channel_context = {
        "persona": video.channel.persona if video.channel else "Default persona",
        "tone": video.channel.tone if video.channel else "Default tone"
    }

    # Video Context
    video_context = {
        "title": video.title,
        "description": video.description,
        "transcript": video.transcript
    }

    # --- New Structured Comments Context Logic ---

    # 1. Separate top-level comments from replies
    top_level_comments = [c for c in video.comments if not c.parent_comment_id]
    replies = [c for c in video.comments if c.parent_comment_id]

    # 2. Create a dictionary to easily look up replies by their parent's ID
    replies_map = {}
    for reply in replies:
        if reply.parent_comment_id not in replies_map:
            replies_map[reply.parent_comment_id] = []
        replies_map[reply.parent_comment_id].append(reply.comment_text)

    # 3. Build the structured list
    structured_comments = []
    for parent in top_level_comments:
        thread = {
            "comment": parent.comment_text,
            "replies": replies_map.get(parent.youtube_comment_id, [])
        }
        structured_comments.append(thread)

    # Combine everything into the final dictionary
    aggregated_data = {
        "channel_context": channel_context,
        "video_context": video_context,
        "comments_context": structured_comments
    }

    return aggregated_data