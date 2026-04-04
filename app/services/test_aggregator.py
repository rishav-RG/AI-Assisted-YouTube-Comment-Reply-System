# test_aggregator.py

from sqlmodel import Session
from app.db.init_db import init_db
from app.db.session import get_session
from app.services.context_aggregator import get_aggregated_context

def run_test():
    """
    Initializes the database, creates a session, and runs the
    get_aggregated_context function to test its output.
    """
    print("--- Starting Aggregator Test ---")

    # 1. Initialize the database (creates tables if they don't exist)
    # This is normally handled by your FastAPI app's lifespan manager.
    print("Initializing database...")
    init_db()
    print("Database initialized.")

    # 2. Get a database session
    # We use the same get_session dependency your app uses.
    db: Session = next(get_session())
    print("Database session created.")

    # 3. Define the video ID you want to test with
    video_id_to_test = 1
    print(f"Attempting to fetch context for video_id: {video_id_to_test}...")

    # 4. Call the function and get the aggregated data
    aggregated_data = get_aggregated_context(db=db, video_id=video_id_to_test)

    # 5. Print the results to the terminal
    if aggregated_data:
        print("\n--- ✅ Aggregated Context Found ---")
        import json
        # Use json.dumps for pretty printing the dictionary
        print(json.dumps(aggregated_data, indent=2))
        print("------------------------------------")
    else:
        print(f"\n--- ⚠️ No data found for video_id: {video_id_to_test} ---")
        print("This might be because the video doesn't exist in your database yet.")
        print("----------------------------------------------------")

    # 6. Close the session
    db.close()
    print("Database session closed.")
    print("--- Test Finished ---")


if __name__ == "__main__":
    run_test()
