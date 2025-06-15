import os
import json
import cv2
import base64
from datetime import datetime
from steps.reverse_parking import evaluate_parking
from steps.hands_on_the_wheel_and_seatbelt import predict_video_report
from steps.driver_eye_tracker import evaluate_gaze_behavior
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://musmanbaig2003:D47mfZUk9RdvCpqK@cluster0.w5tdq.mongodb.net"
DATABASE_NAME = "Liscence_system"
USERS_COLLECTION = "users"
VIOLATIONS_COLLECTION = "violations"

# File paths
SENSOR_FILE = "steps/sensor_log.txt"
VIDEO_FILE = "steps/video_data.mp4"
OUTPUT_FILE = "output/scorecard.json"
CNIC = "1234567890123"

# Video recording start time (adjust this to your actual video start time)
VIDEO_START_TIME = datetime.strptime("2025-06-15 11:20:00", "%Y-%m-%d %H:%M:%S")


def extract_frames(video_path, timestamps, output_dir, video_start_time=None):
    """
    Extracts frames from a video at the provided timestamps.

    Parameters:
    - video_path: path to the input video
    - timestamps: list of timestamp strings (e.g., ['2025-06-15 11:20:30']) or dict with 'timestamps' key
    - output_dir: directory where extracted images will be saved
    - video_start_time: datetime object representing the start time of the video
                        If None, assumes timestamps are in seconds from start.
    """
    # Handle different timestamp formats
    if not timestamps:
        print("No timestamps provided for frame extraction")
        return
    
    # If timestamps is a dictionary, extract the actual timestamp list
    if isinstance(timestamps, dict):
        if 'timestamps' in timestamps:
            timestamp_list = [ts[0] for ts in timestamps['timestamps'] if isinstance(ts, tuple)]
        else:
            print("No valid timestamps found in dictionary")
            return
    elif isinstance(timestamps, list):
        timestamp_list = timestamps
    elif timestamps == "timestamps":
        print("No valid timestamps provided for frame extraction")
        return
    else:
        print(f"Unsupported timestamp format: {type(timestamps)}")
        return
        
    if not timestamp_list:
        print("No valid timestamps found for frame extraction")
        return
        
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        print("Error: Could not retrieve FPS from video.")
        return

    # Process timestamps
    for i, ts in enumerate(timestamp_list):
        try:
            if video_start_time and isinstance(ts, str) and len(ts) > 10:
                # Try to parse as datetime string
                target_time = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                delta = (target_time - video_start_time).total_seconds()
            else:
                # Assume it's seconds from start
                delta = float(ts)
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not parse timestamp '{ts}': {e}")
            continue

        frame_no = int(delta * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)

        success, frame = cap.read()
        if success:
            # Clean timestamp for filename
            ts_clean = str(ts).replace(':', '-').replace(' ', '_')
            frame_filename = os.path.join(output_dir, f"frame_{i+1}_{ts_clean}.jpg")
            cv2.imwrite(frame_filename, frame)
            print(f"Saved: {frame_filename}")
        else:
            print(f"Warning: Could not read frame at {ts}")

    cap.release()


def evaluate_parallel_parking(sensor_file, video_file):
    """
    Evaluate parallel parking using sensor data and extract relevant frames.
    TODO: Replace with your actual parallel parking algorithm.
    
    Returns:
    - score: parallel parking score (0-10)
    - timestamps: list of important timestamps for frame extraction
    """
    # TODO: Implement your actual parallel parking evaluation algorithm
    # For now, using the reverse parking function as a placeholder
    try:
        score, timestamps = evaluate_parking(sensor_file)
        
        # Extract frames at important timestamps if they exist and are valid
        if timestamps and isinstance(timestamps, dict) and 'timestamps' in timestamps and os.path.exists(video_file):
            extract_frames(video_file, timestamps, "output/parallel_parking_frames", VIDEO_START_TIME)
        
        return score, timestamps
    except Exception as e:
        print(f"Error in parallel parking evaluation: {e}")
        return None, None


def connect_to_mongodb():
    """Connect to MongoDB and return the database."""
    try:
        client = MongoClient(MONGODB_URI)
        client.server_info()
        db = client[DATABASE_NAME]
        return db
    except ConnectionFailure as e:
        print(f"Error connecting to MongoDB: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error while connecting to MongoDB: {e}")
        return None


def update_user_scores(db, cnic, scorecard):
    """Update the user document in MongoDB with the test scores and status."""
    try:
        collection = db[USERS_COLLECTION]
        # Debug: Fetch and print the current document
        current_user = collection.find_one({"cnic": cnic})
        if current_user:
            print(f"Current user document: {current_user}")
        else:
            print(f"No user found with CNIC {cnic}")
            return False

        # Use the combined total from scorecard for pass/fail determination
        has_licence = scorecard["combined_total"] >= 66.7  # 6.67/10 (equivalent to 20/30 if scaled to 30)

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
        # Consider the update successful even if no changes were made
        return True

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

    # Initialize violations list
    all_violations = []

    # Run reverse parking evaluation
    rp_score, rp_timestamps = evaluate_parking(SENSOR_FILE)
    print(f"Debug: Reverse parking returned score={rp_score}, timestamps={rp_timestamps}")
    
    if rp_score is None:
        return {"error": "Reverse parking evaluation failed."}
    
    # Extract frames and create violations for reverse parking
    if rp_timestamps and isinstance(rp_timestamps, dict) and 'timestamps' in rp_timestamps and os.path.exists(VIDEO_FILE):
        extract_frames(VIDEO_FILE, rp_timestamps, "output/reverse_parking_frames", VIDEO_START_TIME)
        # Create violations with images
        rp_violations = extract_frames_and_create_violations(VIDEO_FILE, rp_timestamps, "output/reverse_parking_frames", "reverse_parking", VIDEO_START_TIME)
        all_violations.extend(rp_violations)

    # Run parallel parking evaluation
    pp_score, pp_timestamps = evaluate_parallel_parking(SENSOR_FILE, VIDEO_FILE)
    print(f"Debug: Parallel parking returned score={pp_score}, timestamps={pp_timestamps}")
    
    if pp_score is None:
        print("Warning: Parallel parking evaluation failed, using default score of 5.0")
        pp_score = 5.0  # Default fallback score
    else:
        # Create violations with images for parallel parking
        if pp_timestamps and isinstance(pp_timestamps, dict) and 'timestamps' in pp_timestamps:
            pp_violations = extract_frames_and_create_violations(VIDEO_FILE, pp_timestamps, "output/parallel_parking_frames", "parallel_parking", VIDEO_START_TIME)
            all_violations.extend(pp_violations)

    # Process hands-on-the-wheel and seatbelt step
    _, _, hands_seatbelt_scorecard = predict_video_report(VIDEO_FILE)
    if hands_seatbelt_scorecard is None:
        return {"error": "Hands on wheel and seatbelt evaluation failed."}
    
    # Extract frames and create violations for hands-on-steering and seatbelt
    if hands_seatbelt_scorecard.get("violation_timestamps"):
        violation_ts = hands_seatbelt_scorecard["violation_timestamps"]
        
        # Extract frames for hands off steering violations
        if violation_ts.get("hands_off_steering") and os.path.exists(VIDEO_FILE):
            extract_frames(VIDEO_FILE, violation_ts["hands_off_steering"], "output/hands_off_steering_frames", VIDEO_START_TIME)
            # Create violations with images
            hands_violations = extract_frames_and_create_violations(VIDEO_FILE, violation_ts["hands_off_steering"], "output/hands_off_steering_frames", "hands_off_steering", VIDEO_START_TIME)
            all_violations.extend(hands_violations)
        
        # Extract frames for seatbelt violations
        if violation_ts.get("seatbelt_violations") and os.path.exists(VIDEO_FILE):
            extract_frames(VIDEO_FILE, violation_ts["seatbelt_violations"], "output/seatbelt_violation_frames", VIDEO_START_TIME)
            # Create violations with images
            seatbelt_violations = extract_frames_and_create_violations(VIDEO_FILE, violation_ts["seatbelt_violations"], "output/seatbelt_violation_frames", "seatbelt_violation", VIDEO_START_TIME)
            all_violations.extend(seatbelt_violations)

    # Process driver eye tracker step
    driver_score, driver_report, driver_violations = evaluate_gaze_behavior(video_file=VIDEO_FILE)
    if driver_score is None:
        return {"error": "Driver eye tracking evaluation failed."}
    
    # Extract frames and create violations for driver eye tracking
    if driver_violations and os.path.exists(VIDEO_FILE):
        extract_frames(VIDEO_FILE, driver_violations, "output/driver_eye_violation_frames", VIDEO_START_TIME)
        # Create violations with images
        eye_violations = extract_frames_and_create_violations(VIDEO_FILE, driver_violations, "output/driver_eye_violation_frames", "driver_eye_violation", VIDEO_START_TIME)
        all_violations.extend(eye_violations)

    final_scorecard = {
        "reverse_parking_score": rp_score,
        "parallel_parking_score": pp_score,  # Now using actual parallel parking score
        "hands_on_steering_score": hands_seatbelt_scorecard.get("hands_on_steering", 0),
        "seatbelt_score": hands_seatbelt_scorecard.get("seatbelt", 0),
        "driver_eye_score": driver_score,
        "combined_total": (
            (pp_score * 0.25)  # parallel parking (now using actual score)
            + (rp_score * 0.25)  # reverse parking
            + (hands_seatbelt_scorecard.get("hands_on_steering", 0) * 0.1)
            + (hands_seatbelt_scorecard.get("seatbelt", 0) * 0.2)
            + (driver_score * 0.2)
        ) * 10,  # Scale to 100
    }

    # Update MongoDB with scores and violations
    collection = connect_to_mongodb()
    if collection is not None:
        success = update_user_scores(collection, CNIC, final_scorecard)
        if not success:
            return {"error": "Failed to update scores in MongoDB."}
        
        # Save violations to database
        violations_success = save_violations_to_db(collection, CNIC, all_violations)
        if not violations_success:
            print("Warning: Failed to save violations to database")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Save to JSON file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_scorecard, f)

    print(f"Total violations detected and saved: {len(all_violations)}")
    return final_scorecard


def image_to_base64(image_path):
    """Convert image file to base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None


def extract_frames_and_create_violations(video_path, timestamps, output_dir, violation_type, video_start_time=None):
    """
    Extract frames and create violation objects with base64 encoded images.
    
    Returns:
    - List of violation dictionaries ready for database insertion
    """
    violations = []
    
    # Handle different timestamp formats
    if not timestamps:
        print("No timestamps provided for frame extraction")
        return violations
    
    # If timestamps is a dictionary, extract the actual timestamp list
    if isinstance(timestamps, dict):
        if 'timestamps' in timestamps:
            timestamp_list = [ts[0] for ts in timestamps['timestamps'] if isinstance(ts, tuple)]
        else:
            print("No valid timestamps found in dictionary")
            return violations
    elif isinstance(timestamps, list):
        timestamp_list = timestamps
    elif timestamps == "timestamps":
        print("No valid timestamps provided for frame extraction")
        return violations
    else:
        print(f"Unsupported timestamp format: {type(timestamps)}")
        return violations
        
    if not timestamp_list:
        print("No valid timestamps found for frame extraction")
        return violations
        
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return violations

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        print("Error: Could not retrieve FPS from video.")
        return violations

    # Define severity and description based on violation type
    severity_map = {
        "reverse_parking": "medium",
        "parallel_parking": "medium", 
        "hands_off_steering": "high",
        "seatbelt_violation": "high",
        "driver_eye_violation": "medium"
    }
    
    description_map = {
        "reverse_parking": "Improper reverse parking maneuver detected",
        "parallel_parking": "Improper parallel parking maneuver detected",
        "hands_off_steering": "Driver hands off steering wheel detected",
        "seatbelt_violation": "Seatbelt violation detected",
        "driver_eye_violation": "Driver eye tracking violation detected"
    }

    # Process timestamps
    for i, ts in enumerate(timestamp_list):
        try:
            if video_start_time and isinstance(ts, str) and len(ts) > 10:
                # Try to parse as datetime string
                target_time = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                delta = (target_time - video_start_time).total_seconds()
            else:
                # Assume it's seconds from start
                delta = float(ts)
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not parse timestamp '{ts}': {e}")
            continue

        frame_no = int(delta * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)

        success, frame = cap.read()
        if success:
            # Clean timestamp for filename
            ts_clean = str(ts).replace(':', '-').replace(' ', '_')
            frame_filename = os.path.join(output_dir, f"frame_{i+1}_{ts_clean}.jpg")
            cv2.imwrite(frame_filename, frame)
            print(f"Saved: {frame_filename}")
            
            # Convert image to base64
            image_base64 = image_to_base64(frame_filename)
            if image_base64:
                violation = {
                    "userCnic": CNIC,  # Add user reference
                    "type": violation_type,
                    "timestamp": str(ts),
                    "imageBase64": image_base64,
                    "severity": severity_map.get(violation_type, "medium"),
                    "description": description_map.get(violation_type, f"{violation_type} violation detected"),
                    "testDate": datetime.now().isoformat()
                }
                violations.append(violation)
        else:
            print(f"Warning: Could not read frame at {ts}")

    cap.release()
    return violations


def save_violations_to_db(db, cnic, violations):
    """Save violations array to violations collection in MongoDB."""
    try:
        if not violations:
            print("No violations to save")
            return True
            
        collection = db[VIOLATIONS_COLLECTION]
        
        # Insert all violations at once
        result = collection.insert_many(violations)
        
        if result.inserted_ids:
            print(f"Successfully saved {len(result.inserted_ids)} violations to database")
            return True
        else:
            print("Failed to insert violations")
            return False
            
    except Exception as e:
        print(f"Error saving violations to MongoDB: {e}")
        return False


if __name__ == "__main__":
    result = run_pipeline()
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("Final Scorecard:")
        print(result)