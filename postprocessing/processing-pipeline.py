import os
import json
from steps.reverse_parking import evaluate_parking
from steps.hands_on_the_wheel_and_seatbelt import predict_video_report
from steps.driver_eye_tracker import evaluate_gaze_behavior
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://musmanbaig2003:D47mfZUk9RdvCpqK@cluster0.w5tdq.mongodb.net"
DATABASE_NAME = "Liscence_system"
COLLECTION_NAME = "users"

# File paths
SENSOR_FILE = "steps/sensor_log.txt"
VIDEO_FILE = "steps/video_data.mp4"
OUTPUT_FILE = "output/scorecard.json"
CNIC = "1234567890123"


def connect_to_mongodb():
    """Connect to MongoDB and return the users collection."""
    try:
        client = MongoClient(MONGODB_URI)
        client.server_info()
        db = client[DATABASE_NAME]
        return db[COLLECTION_NAME]
    except ConnectionFailure as e:
        print(f"Error connecting to MongoDB: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error while connecting to MongoDB: {e}")
        return None


def update_user_scores(collection, cnic, scorecard):
    """Update the user document in MongoDB with the test scores and status."""
    try:
        # Use the combined total from scorecard for pass/fail determination
        has_licence = scorecard["combined_total"] >= 66.7  # equivalent to 20/30

        update_result = collection.update_one(
            {"cnic": cnic},
            {
                "$set": {
                    "reverseParkingScore": scorecard["reverse_parking_score"],
                    "parallelParkingScore": scorecard["parallel_parking_score"],
                    "handsOnSteeringScore": scorecard["hands_on_steering_score"],
                    "seatbeltScore": scorecard["seatbelt_score"],
                    "driverEyeScore": scorecard["driver_eye_score"],
                    "totalScore": round(scorecard["combined_total"], 2),
                    "testCompleted": True,
                    "hasLicence": has_licence,
                    "passTest": has_licence,
                    "hasLearnerLicence": False,
                }
            },
        )

        if update_result.matched_count == 0:
            print(f"No user found with CNIC {cnic}")
            return False
        return update_result.modified_count > 0

    except Exception as e:
        print(f"Error updating MongoDB: {e}")
        return False


def run_pipeline():
    """Run the preprocessing pipeline and update MongoDB with the results."""
    # Validate file paths
    if not os.path.exists(SENSOR_FILE):
        return {"error": f"Sensor file {SENSOR_FILE} does not exist."}
    if not os.path.exists(VIDEO_FILE):
        return {"error": f"Video file {VIDEO_FILE} does not exist."}

    # Run reverse parking evaluation
    rp_score, _ = evaluate_parking(SENSOR_FILE)
    if rp_score is None:
        return {"error": "Reverse parking evaluation failed."}

    # Process hands-on-the-wheel and seatbelt step
    _, _, hands_seatbelt_scorecard = predict_video_report(VIDEO_FILE)
    if hands_seatbelt_scorecard is None:
        return {"error": "Hands on wheel and seatbelt evaluation failed."}

    # Process driver eye tracker step
    driver_score, _ = evaluate_gaze_behavior(video_file=VIDEO_FILE)
    if driver_score is None:
        return {"error": "Driver eye tracking evaluation failed."}

    final_scorecard = {
        "reverse_parking_score": rp_score,
        "parallel_parking_score": 10,
        "hands_on_steering_score": hands_seatbelt_scorecard.get("hands_on_steering", 0),
        "seatbelt_score": hands_seatbelt_scorecard.get("seatbelt", 0),
        "driver_eye_score": driver_score,
        "combined_total": (
            (10 * 0.25)  # parallel parking
            + (rp_score * 0.25)  # reverse parking
            + (hands_seatbelt_scorecard.get("hands_on_steering", 0) * 0.1)
            + (hands_seatbelt_scorecard.get("seatbelt", 0) * 0.2)
            + (driver_score * 0.2)
        )
        * 10,
    }

    # Update MongoDB - fixed collection check
    collection = connect_to_mongodb()
    if collection is not None:  # Changed from if collection:
        success = update_user_scores(collection, CNIC, final_scorecard)
        if not success:
            return {"error": "Failed to update scores in MongoDB."}

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Save to JSON file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_scorecard, f)

    return final_scorecard


if __name__ == "__main__":
    result = run_pipeline()
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("Final Scorecard:")
        print(result)
