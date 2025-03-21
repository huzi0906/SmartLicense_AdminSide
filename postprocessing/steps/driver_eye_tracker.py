import cv2
import mediapipe as mp
import numpy as np
import time
import os


def evaluate_gaze_behavior(duration=60, reverse_phase=20, video_file=None):
    """
    Evaluates driver's gaze behavior over a given duration and returns a final score with a detailed report.
    If the video duration is shorter than `duration`, it uses the available seconds.
    Processed video is saved in the output/ folder.

    Parameters:
      duration (int): Total test duration in seconds (default 60s).
      reverse_phase (int): Duration at the end for the reverse parking phase in seconds (default 20s).

    Returns:
      final_score (float): Score out of 10.
      report (str): Detailed report of the evaluation including reverse parking analysis.
    """

    # Initialize Mediapipe Face Mesh
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
    mp_drawing = mp.solutions.drawing_utils

    # Iris landmark indices
    left_iris_indices = [474, 475, 476, 477]
    right_iris_indices = [469, 470, 471, 472]

    # Video capture
    # cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        raise ValueError("Error opening video file")

    # Retrieve video properties
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Create output folder if it doesn't exist and define output video file
    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", "driver_eye_output.webm")
    out_writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"vp80"),
        fps,
        (frame_width, frame_height),
    )

    # Scoring variables
    initial_score = 10.0
    penalty_forward = 0.0  # Penalty for not looking forward enough
    penalty_continuous = 0.0  # Penalty for continuous side gazes > 5s
    penalty_reverse = 0.0  # Penalty for insufficient side checking in reverse phase

    # Timing accumulators (in seconds)
    total_time = 0.0
    forward_time = 0.0
    left_time = 0.0
    right_time = 0.0
    reverse_side_time = 0.0  # Time in last phase looking left or right

    # For tracking continuous side gaze events
    current_side_state = None  # can be "left" or "right" or None (if forward)
    continuous_start = None
    continuous_events = []  # list of tuples: (state, duration)

    # Timestamp markers
    test_start = time.time()
    last_frame_time = test_start

    # List to record per-frame states for reverse phase analysis
    frame_records = (
        []
    )  # each record: (timestamp, state) where state in ["forward", "left", "right"]

    def get_landmark_coords(landmarks, indices, iw, ih):
        coords = []
        for idx in indices:
            x = int(landmarks.landmark[idx].x * iw)
            y = int(landmarks.landmark[idx].y * ih)
            coords.append((x, y))
        return coords

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        dt = current_time - last_frame_time
        last_frame_time = current_time
        total_time = current_time - test_start

        # Convert image to RGB and process with Mediapipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)

        # Default state
        state = "forward"

        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            ih, iw, _ = frame.shape

            # Get iris coordinates
            left_iris = get_landmark_coords(face_landmarks, left_iris_indices, iw, ih)
            right_iris = get_landmark_coords(face_landmarks, right_iris_indices, iw, ih)

            # Compute centers of eyes
            left_center = np.mean(left_iris, axis=0).astype(int)
            right_center = np.mean(right_iris, axis=0).astype(int)

            # Use nose tip (landmark index 1) for reference
            nose_tip = face_landmarks.landmark[1]
            nose_coords = (int(nose_tip.x * iw), int(nose_tip.y * ih))

            # Calculate gaze ratio using horizontal displacement
            left_ratio = (left_center[0] - nose_coords[0]) / iw
            right_ratio = (right_center[0] - nose_coords[0]) / iw
            avg_ratio = (left_ratio + right_ratio) / 2

            # Determine state based on threshold
            if avg_ratio > 0.015:
                state = "right"
            elif avg_ratio < -0.015:
                state = "left"
            else:
                state = "forward"

        # Accumulate time based on state
        if state == "forward":
            forward_time += dt
        elif state == "left":
            left_time += dt
        elif state == "right":
            right_time += dt

        # Record frame state (for reverse phase analysis)
        frame_records.append((total_time, state))

        # Track continuous side gaze events
        if state in ["left", "right"]:
            if current_side_state is None:
                # Start a new side event
                current_side_state = state
                continuous_start = current_time
            elif current_side_state != state:
                # Switched side; finalize previous event
                duration_event = current_time - continuous_start
                if duration_event > 5.0:
                    continuous_events.append((current_side_state, duration_event))
                # Reset for new event
                current_side_state = state
                continuous_start = current_time
            # else: state remains the same, continue
        else:
            # If state is forward, finalize any running side event
            if current_side_state is not None:
                duration_event = current_time - continuous_start
                if duration_event > 5.0:
                    continuous_events.append((current_side_state, duration_event))
                current_side_state = None
                continuous_start = None

        # Instead of showing cv2 window, write annotated frame (with state text) to output video.
        cv2.putText(
            frame,
            f"State: {state}",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        out_writer.write(frame)

        # Stop the loop after the set duration
        if total_time >= duration:
            break

    # End capture
    cap.release()
    out_writer.release()
    cv2.destroyAllWindows()

    # Finalize any ongoing side event if test ends during one
    if current_side_state is not None:
        duration_event = time.time() - continuous_start
        if duration_event > 5.0:
            continuous_events.append((current_side_state, duration_event))

    # Calculate reverse phase side gaze time based on frame records
    for t, st in frame_records:
        if t >= (total_time - reverse_phase) and st in ["left", "right"]:
            # Approximate each frame's duration (assuming 30 FPS)
            reverse_side_time += 1.0 / 30.0

    # Calculate penalties:
    # 1. Forward gaze requirement: at least 60% of total time should be forward.
    required_forward = 0.6 * total_time
    if forward_time < required_forward:
        penalty_forward = (
            2.0  # Deduct 2 points if forward gaze time is below threshold.
        )

    # 2. Continuous side gaze penalty: 1 point per occurrence where side gaze was maintained for >5s.
    penalty_continuous = len(continuous_events) * 1.0

    # 3. Reverse phase check: In the last reverse_phase seconds, side gaze should account for at least 25% of that time.
    reverse_percentage = (reverse_side_time / reverse_phase) * 100
    if reverse_side_time < 0.25 * reverse_phase:
        penalty_reverse = 2.0  # Deduct 2 points.

    # Sum penalties and calculate final score
    total_penalty = penalty_forward + penalty_continuous + penalty_reverse
    final_score = max(0.0, initial_score - total_penalty)

    # Create detailed report
    report_lines = [
        "Gaze Behavior Evaluation Report:",
        f"Total Test Duration: {total_time:.2f} seconds",
        "",
        "General Gaze Behavior:",
        f"  - Time Looking Forward: {forward_time:.2f} seconds ({(forward_time/total_time)*100:.1f}%)",
        f"  - Time Looking Left: {left_time:.2f} seconds",
        f"  - Time Looking Right: {right_time:.2f} seconds",
        f"  - Continuous Side Gaze Events (>5s): {len(continuous_events)}",
        "",
        "Penalties:",
        f"  - Forward Gaze Deficit Penalty: {penalty_forward} point(s)",
        f"  - Continuous Side Gaze Penalty: {penalty_continuous} point(s)",
        "",
        "Reverse Parking Phase Analysis (Last {} seconds):".format(reverse_phase),
        f"  - Total Reverse Phase Duration: {reverse_phase} seconds",
        f"  - Time Spent Looking Sideways: {reverse_side_time:.2f} seconds",
        f"  - Percentage of Reverse Phase with Side Gaze: {reverse_percentage:.1f}%",
        f"  - Reverse Phase Penalty (if <25% side gaze): {penalty_reverse} point(s)",
        "",
        f"Final Score: {final_score:.2f}/10",
    ]
    report = "\n".join(report_lines)

    return final_score, report


# For direct testing:
if __name__ == "__main__":
    score, evaluation_report = evaluate_gaze_behavior()
    print(evaluation_report)