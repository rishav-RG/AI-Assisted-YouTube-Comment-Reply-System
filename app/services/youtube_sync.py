# FULL PIPELINE (main brain)

from sqlmodel import Session, select

from app.db.models import UserYouTubeAuth
from app.youtube.client import get_youtube_client
from app.youtube.channel import fetch_channel_data
from app.youtube.videos import fetch_videos
from app.youtube.comments import fetch_comments_with_replies
from app.youtube.transcript import fetch_transcript

from app.crud.channel import upsert_channel
from app.crud.video import upsert_video
from app.crud.comment import upsert_comment


async def sync_youtube(user_id: int, session: Session):
    '''
    Synchronizes a user's YouTube data using a modular CRUD-based approach.

    This function retrieves the user's YouTube data via the YouTube API and
    delegates database operations (insert/update) to dedicated CRUD functions.
    It ensures that channel, video, transcript, and comment data are kept
    up-to-date in the database.

    Workflow:
    1. Fetch the user's stored YouTube OAuth credentials.
    2. Create an authenticated YouTube API client.
    3. Fetch channel data and upsert it using `upsert_channel`.
    4. Fetch all videos for the channel.
    5. For each video:
        a. Upsert video metadata using `upsert_video`.
        b. Fetch and update transcript (if available).
        c. Fetch comments for the video.
        d. Upsert each comment using `upsert_comment`.

    Args:
        user_id (int): ID of the user whose YouTube data is being synchronized.
        session (Session): Database session used for CRUD operations.

    Returns:
        None

    Notes:
    - Uses a separation of concerns approach by delegating database logic to CRUD functions.
    - Improves code readability, reusability, and maintainability compared to inline DB logic.
    - Assumes CRUD functions handle upsert logic (insert or update) internally.
    - Transcript updates are committed immediately if present.
    - Error handling for missing YouTube authentication should be handled externally.
    '''
    user_auth = session.exec(
        select(UserYouTubeAuth).where(UserYouTubeAuth.user_id == user_id)
    ).first()

    youtube = await get_youtube_client(user_auth, session)

    channel_data = fetch_channel_data(youtube)
    channel = upsert_channel(session, user_id, channel_data)

    videos = fetch_videos(youtube, channel_data["youtube_channel_id"])

    for v in videos:
        video = upsert_video(session, user_id, channel.id, v)

        transcript = fetch_transcript(v["youtube_video_id"])
        if transcript:
            video.transcript = transcript
            session.add(video)
            session.commit()

        comments = fetch_comments_with_replies(youtube, v["youtube_video_id"])

        for c in comments:
            upsert_comment(session, user_id, video.id, c)