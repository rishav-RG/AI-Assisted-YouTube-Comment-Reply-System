# For making authenticated Youtube API client for a user
# which can be used to make Youtube API calls

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone

from app.youtube.oauth import refresh_access_token


async def get_youtube_client(user_auth, session):
    '''
    Returns an authenticated YouTube API client for a user.

    This function ensures that the user's access token is valid before creating
    the client. If the access token has expired, it uses the stored refresh token
    to obtain a new access token and updates it in the database.

    Steps performed:
    1. Check if the current access token is expired.
    2. If expired, refresh it using the refresh token.
    3. Update and persist the new access token in the database.
    4. Create OAuth credentials using the valid tokens.
    5. Return a YouTube Data API client authenticated for the user.

    Args:
        user_auth: Database object containing user's OAuth tokens and expiry.
        session: Database session used to update stored tokens.

    Returns:
        googleapiclient.discovery.Resource:
        An authenticated YouTube API client for making API requests on behalf of the user.
    '''
    if user_auth.expiry and user_auth.expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        token_data = await refresh_access_token(user_auth.refresh_token)

        user_auth.access_token = token_data["access_token"]
        session.add(user_auth)
        session.commit()

    credentials = Credentials(
        token=user_auth.access_token,
        refresh_token=user_auth.refresh_token,
        token_uri="https://oauth2.googleapis.com/token"
    )

    # build() = “Give me a ready-to-use YouTube API client authenticated with this user.”
    return build("youtube", "v3", credentials=credentials)