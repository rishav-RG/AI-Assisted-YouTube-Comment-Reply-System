# test_aggregator.py

from sqlmodel import Session
from app.db.init_db import init_db
from app.db.session import get_session
from app.services.context_aggregator import get_aggregated_context

def run_test():
    """
    Connects to the existing database, creates a session, and runs the
    get_aggregated_context function to test its output.

    This script assumes your main FastAPI application is or has been running
    to ensure the database is initialized and populated.
    """
    print("--- Starting Aggregator Test ---")

    db: Session | None = None
    try:
        # 1. Get a database session
        # This creates a new connection to the database defined in your config.
        print("Attempting to connect to the database...")
        db = next(get_session())
        print("Database session created successfully.")

        # 2. Define the video ID you want to test with
        video_id_to_test = 2
        print(f"Fetching context for video_id: {video_id_to_test}...")

        # 3. Call the function and get the aggregated data
        aggregated_data = get_aggregated_context(db=db, video_id=video_id_to_test)

        # 4. Print the results to the terminal
        if aggregated_data:
            import json
            print("\n--- ✅ Aggregated Context Found ---")
            # Use json.dumps for pretty printing the dictionary
            print(json.dumps(aggregated_data, indent=2))
            print("------------------------------------")
        else:
            print(f"\n--- ⚠️ No data found for video_id: {video_id_to_test} ---")
            print("This might be because the video doesn't exist in your database yet.")
            print("Ensure you have run the sync process first.")
            print("----------------------------------------------------")

    except Exception as e:
        print("\n--- ❌ An error occurred ---")
        print("Could not connect to the database or an error occurred during execution.")
        print("Please ensure the database server is running and accessible.")
        print(f"Error details: {e}")
        print("-----------------------------")
    finally:
        # 5. Close the session if it was successfully created
        if db:
            db.close()
            print("Database session closed.")
    
    print("--- Test Finished ---")


if __name__ == "__main__":
    run_test()
