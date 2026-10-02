import asyncio
from app.services.comment_labeling_pipeline import CommentLabelingPipeline
from app.db.session import get_session
from app.db.models import Video
from app.services.context_aggregator import get_comments_aggregated


async def main():
    session = next(get_session())
    pipeline = CommentLabelingPipeline()
    result = await pipeline.run_full_pipeline(
        session=session,
        user_id=1,      # Use a valid user_id
        video_id=2,   # Use a valid video_id from your DB
    )
    print(result)


# async def test_flattening():
#     """
#     Tests the flattening logic for comment threads and raw comments
#     to ensure IDs are correctly processed.
#     """
#     print("--- Running test_flattening ---")
#     session = next(get_session())
#     print("got session")
#     pipeline = CommentLabelingPipeline()



#     # --- Test _flatten_threads ---
#     # Use a valid video_id from your database
#     video = session.get(Video, 2)
#     if not video:
#         print("Video with ID 2 not found. Skipping _flatten_threads test.")
#     else:
#         print(f"\nFound video: '{video.title}'")
#         aggregated_comments = get_comments_aggregated(video)
#         print("\n1. Aggregated comments (from get_comments_aggregated):")
#         # print(aggregated_comments) # Uncomment for full details

#         flattened_threads = pipeline._flatten_threads(aggregated_comments)
#         print("\n2. Result of _flatten_threads (should have 'id' for comments and replies):")
#         print(flattened_threads)

#     # --- Test _from_raw_comments ---
#     raw_comments = ["This is the first raw comment.", "Here is another one.", "And a final raw comment."]
#     print("\n3. Raw comments (input):")
#     print(raw_comments)

#     flattened_raw = pipeline._from_raw_comments(raw_comments)
#     print("\n4. Result of _from_raw_comments (no 'id' expected):")
#     print(flattened_raw)
#     print("\n--- Test finished ---")


if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.run(main())

