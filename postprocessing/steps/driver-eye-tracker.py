import cv2
import mediapipe as mp
import numpy as np

# Initialize Mediapipe Face Mesh with refine_landmarks=True to get iris landmarks
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
mp_drawing = mp.solutions.drawing_utils

# Indices for left and right iris landmarks
left_iris_indices = [474, 475, 476, 477]
right_iris_indices = [469, 470, 471, 472]

# Capture video
cap = cv2.VideoCapture(0)

# Desired window size
window_width, window_height = 1280, 960


# Function to resize frames
def resize_frame(frame, width, height):
    return cv2.resize(frame, (width, height))


while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Convert the image to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    # Create copies for each step
    face_mesh_frame = frame.copy()
    eye_detection_frame = frame.copy()
    gaze_detection_frame = frame.copy()

    if results.multi_face_landmarks:
        face_landmarks = results.multi_face_landmarks[0]

        # Draw face mesh landmarks
        mp_drawing.draw_landmarks(
            face_mesh_frame, face_landmarks, mp_face_mesh.FACEMESH_TESSELATION
        )

        # Get image dimensions
        ih, iw, _ = frame.shape

        # Helper function to get coordinates
        def get_landmark_coords(indices):
            coords = []
            for idx in indices:
                x = int(face_landmarks.landmark[idx].x * iw)
                y = int(face_landmarks.landmark[idx].y * ih)
                coords.append((x, y))
            return coords

        # Get left and right iris coordinates
        left_iris = get_landmark_coords(left_iris_indices)
        right_iris = get_landmark_coords(right_iris_indices)

        # Draw iris landmarks
        for coord in left_iris:
            cv2.circle(eye_detection_frame, coord, 2, (0, 255, 0), -1)
        for coord in right_iris:
            cv2.circle(eye_detection_frame, coord, 2, (0, 255, 0), -1)

        # Calculate the center of the eyes
        left_center = np.mean(left_iris, axis=0).astype(int)
        right_center = np.mean(right_iris, axis=0).astype(int)
        cv2.circle(eye_detection_frame, tuple(left_center), 2, (0, 0, 255), -1)
        cv2.circle(eye_detection_frame, tuple(right_center), 2, (0, 0, 255), -1)

        # Extract eye regions
        eye_margin = 30
        left_eye_region = frame[
            max(0, left_center[1] - eye_margin) : min(ih, left_center[1] + eye_margin),
            max(0, left_center[0] - eye_margin) : min(iw, left_center[0] + eye_margin),
        ]
        right_eye_region = frame[
            max(0, right_center[1] - eye_margin) : min(
                ih, right_center[1] + eye_margin
            ),
            max(0, right_center[0] - eye_margin) : min(
                iw, right_center[0] + eye_margin
            ),
        ]

        # Calculate gaze direction
        nose_tip = face_landmarks.landmark[1]
        nose_coords = (
            int(nose_tip.x * iw),
            int(nose_tip.y * ih),
        )

        # Calculate ratios
        left_ratio = (left_center[0] - nose_coords[0]) / iw
        right_ratio = (right_center[0] - nose_coords[0]) / iw

        avg_ratio = (left_ratio + right_ratio) / 2

        if avg_ratio > 0.015:
            gaze_direction = "Looking Right"
        elif avg_ratio < -0.015:
            gaze_direction = "Looking Left"
        else:
            gaze_direction = "Looking Forward"
        gaze_direction += f" ({avg_ratio:.4f})"

        # Display gaze direction on the window
        cv2.putText(
            gaze_detection_frame,
            gaze_direction,
            (50, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,  # Increase font size
            (0, 255, 0),
            3,
            cv2.LINE_AA,
        )

        # Draw gaze line
        cv2.line(
            gaze_detection_frame,
            tuple(left_center),
            tuple(right_center),
            (255, 0, 0),
            2,
        )
    else:
        # If no face is detected, create blank images for eye regions
        left_eye_region = np.zeros((60, 60, 3), dtype=np.uint8)
        right_eye_region = np.zeros((60, 60, 3), dtype=np.uint8)

    # Resize frames to fill the window
    frame_width, frame_height = window_width // 2, window_height // 2
    face_mesh_frame = resize_frame(face_mesh_frame, frame_width, frame_height)
    eye_detection_frame = resize_frame(eye_detection_frame, frame_width, frame_height)
    gaze_detection_frame = resize_frame(gaze_detection_frame, frame_width, frame_height)

    # Resize eye regions to match the height
    eye_width = frame_width // 2
    left_eye_region = resize_frame(left_eye_region, eye_width, frame_height)
    right_eye_region = resize_frame(right_eye_region, eye_width, frame_height)

    # Stack eye regions horizontally
    eyes_combined = np.hstack((left_eye_region, right_eye_region))

    # Stack frames horizontally and vertically
    top_row = np.hstack((face_mesh_frame, eyes_combined))
    bottom_row = np.hstack((eye_detection_frame, gaze_detection_frame))
    combined_frame = np.vstack((top_row, bottom_row))

    # Create window with fixed size
    cv2.namedWindow("Results", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Results", window_width, window_height)

    # Show the combined frame
    cv2.imshow("Results", combined_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
