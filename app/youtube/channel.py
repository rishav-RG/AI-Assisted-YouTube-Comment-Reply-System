# For fetching channel data through Youtube API
def fetch_channel_data(youtube):
    response = youtube.channels().list(
        part="snippet,statistics",
        mine=True
    ).execute()

    item = response["items"][0]

    return {
        "youtube_channel_id": item["id"],
        "channel_name": item["snippet"]["title"],
        "description": item["snippet"]["description"]
    }