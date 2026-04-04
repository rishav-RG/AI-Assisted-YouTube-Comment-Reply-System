# app/services/context_aggregator.py

from sqlmodel import Session, select
from app.db.models import Video

def get_aggregated_context(db: Session, video_id: int) -> dict:
    """
    Aggregates all relevant text context for a given video to be used in a RAG pipeline.

    This function queries the database for a specific video and gathers:
    1.  Channel Context: The pre-defined persona and tone for the channel.
    2.  Video Context: The video's title, description, and full transcript.
    3.  Comments Context: The text from all existing comments on that video.

    Args:
        db (Session): The database session to use for querying.
        video_id (int): The ID of the video to aggregate context for.

    Returns:
        dict: A dictionary containing the structured text context, or an empty
              dictionary if the video is not found.
    """
    
    # 1. Fetch the video and its related data in one go.
    # SQLModel's relationships (like video.channel and video.comments)
    # allow us to access related objects easily.
    video = db.get(Video, video_id)

    if not video:
        return {}

    # 2. Extract the different layers of context.
    
    # Channel Context from the related Channel object
    channel_context = {
        "persona": video.channel.persona if video.channel else "Default persona",
        "tone": video.channel.tone if video.channel else "Default tone"
    }

    # Video Context directly from the Video object
    video_context = {
        "title": video.title,
        "description": video.description,
        "transcript": video.transcript
    }

    # Comments Context by iterating through the related Comment objects
    comments_context = [
        comment.comment_text for comment in video.comments
    ]

    # 3. Combine everything into a single, structured dictionary.
    # This format is clean and easy to pass to the next step in your RAG pipeline.
    aggregated_data = {
        "channel_context": channel_context,
        "video_context": video_context,
        "comments_context": comments_context
    }

    return aggregated_data
