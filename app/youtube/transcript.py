from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

def fetch_transcript(video_id: str) -> str | None:
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except NoTranscriptFound:
            for available_transcript in transcript_list:
                transcript = available_transcript 
                break 

        # Step 4: Fetch the data
        transcript_data = transcript.fetch()
        
        # 🔥 The Fix: Safely handle both new Objects (t.text) and old Dictionaries (t["text"])
        return " ".join([
            t.text if hasattr(t, 'text') else t["text"] 
            for t in transcript_data
        ])

    except TranscriptsDisabled:
        print(f"⚠️ Transcripts disabled by creator for video: {video_id}")
        return None
    except VideoUnavailable:
        print(f"⚠️ Video {video_id} is unavailable (deleted or private).")
        return None
    except NoTranscriptFound:
        print(f"⚠️ Absolutely no transcripts found for {video_id}.")
        return None
    except Exception as e:
        print(f"❌ Unexpected error fetching transcript for {video_id}: {e}")
        return None