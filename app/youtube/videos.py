# For fetching video from Youtube API 

def fetch_videos(youtube, channel_id):
    response = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=10,
        order="date",
        type="video"
    ).execute()

    return [
        {
            "youtube_video_id": v["id"]["videoId"],
            "title": v["snippet"]["title"],
            "description": v["snippet"]["description"]
        }
        for v in response["items"]
    ]