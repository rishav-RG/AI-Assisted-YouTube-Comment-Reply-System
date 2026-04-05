# For fetching comments from Youtube API
from typing import List, Dict


def fetch_replies(youtube, parent_id: str) -> List[Dict]:
    """
    Fetch all replies for a given parent comment
    """
    replies = []

    response = youtube.comments().list(
        part="snippet",
        parentId=parent_id,
        maxResults=100,
        textFormat="plainText"
    ).execute()

    for r in response.get("items", []):
        snippet = r["snippet"]

        replies.append({
            "youtube_comment_id": r["id"],
            "comment_text": snippet["textDisplay"],
            "author": snippet["authorDisplayName"],
            "author_channel_id": snippet["authorChannelId"]["value"],
            "parent_comment_id": parent_id
        })

    return replies


def fetch_comments_with_replies(youtube, video_id: str) -> List[Dict]:
    """
    Fetch top-level comments and ALL their replies
    """
    comments = []

    response = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=20, # have to do pagination
        textFormat="plainText"
    ).execute()

    for item in response.get("items", []):
        top = item["snippet"]["topLevelComment"]
        top_snippet = top["snippet"]

        parent_id = top["id"]

        # Top-level comment
        comments.append({
            "youtube_comment_id": parent_id,
            "comment_text": top_snippet["textDisplay"],
            "author": top_snippet["authorDisplayName"],
            "author_channel_id": top_snippet["authorChannelId"]["value"],
            "parent_comment_id": None
        })

        # Fetch ALL replies separately
        replies = fetch_replies(youtube, parent_id)
        comments.extend(replies)
    print("comments:", comments)
    return comments