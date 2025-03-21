from ultralytics import YOLO
import cv2
import os
import pandas as pd
import re  # needed for scorecard processing

# Load the YOLO model
model = YOLO("steps/weights/best.pt")


def process_video(video_path):
    # print("[DEBUG] Starting process_video with video_path:", video_path)
    if not video_path:
        # print("[DEBUG] No video_path provided.")
        return None, None

    try:
        video_capture = cv2.VideoCapture(video_path)
        if not video_capture.isOpened():
            raise ValueError("Error opening video file")

        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(video_capture.get(cv2.CAP_PROP_FPS))
        # print(f"[DEBUG] Video properties: {frame_width}x{frame_height} at {fps} FPS")

        os.makedirs("output", exist_ok=True)
        output_path = os.path.join("output", "hands_on_the_wheel_seatbelt.webm")
        output_video = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*"vp80"),
            fps,
            (frame_width, frame_height),
        )

        frame_count = 0
        frame_skip_counter = 0
        second_annotations = {}
        last_valid_annotations = None

        while True:
            ret, frame = video_capture.read()
            if not ret:
                break

            timestamp = frame_count / fps
            second = int(timestamp)
            # Debug: track frame count and assigned second
            # if frame_count % 50 == 0:
            #     print(
            #         f"[DEBUG] Processing frame {frame_count} at {timestamp:.2f}s (second {second})"
            #     )

            if frame_skip_counter % 4 == 0:
                results = model.predict(source=frame, verbose=False)
                if len(results[0].boxes) > 0:
                    current_detections = []
                    for result in results[0].boxes:
                        annotation = model.names[int(result.cls)]
                        annotation = annotation.replace("_", " ").capitalize()
                        confidence = float(result.conf) * 100
                        current_detections.append([annotation, second, confidence])
                        # print(
                        #     f"[DEBUG] Detected: {annotation} at second {second} with {confidence:.1f}%"
                        # )
                    second_annotations[second] = current_detections
                    last_valid_annotations = current_detections
                elif last_valid_annotations and second not in second_annotations:
                    # print(
                    #     f"[DEBUG] No new detection at second {second}, using last valid annotations."
                    # )
                    second_annotations[second] = last_valid_annotations
                annotated_frame = results[0].plot()
            else:
                annotated_frame = frame

            output_video.write(annotated_frame)
            frame_count += 1
            frame_skip_counter += 1

        video_capture.release()
        output_video.release()
        # print("[DEBUG] Finished video capture. Total frames processed:", frame_count)

        if not second_annotations:
            # print("[DEBUG] No annotations found.")
            return output_path, None

        annotations_dict = {}
        max_second = max(second_annotations.keys())
        # print(f"[DEBUG] Max second identified: {max_second}")

        for s in range(max_second + 1):
            if s in second_annotations:
                for ann in second_annotations[s]:
                    if ann[0] not in annotations_dict:
                        annotations_dict[ann[0]] = []
                    annotations_dict[ann[0]].append((ann[1], ann[2]))
            elif last_valid_annotations:
                for ann in last_valid_annotations:
                    if ann[0] not in annotations_dict:
                        annotations_dict[ann[0]] = []
                    annotations_dict[ann[0]].append((s, ann[2]))

        detection_data = []
        for annotation, times_confidences in annotations_dict.items():
            times_str = ", ".join(
                [f"[ Time: {t}s, Confidence: {c:.1f}% ]" for t, c in times_confidences]
            )
            detection_data.append([annotation, times_str])
            # print(f"[DEBUG] Annotation {annotation}: {times_str}")

        df = pd.DataFrame(detection_data, columns=["Annotation", "Details"])
        # print("[DEBUG] process_video returning output video at", output_path)
        return output_path, df

    except Exception as e:
        # print(f"Error processing video: {str(e)}")
        return None, None


def get_longest_consecutive(times):
    if not times:
        return 0
    times = sorted(times)
    longest = 1
    current = 1
    for i in range(len(times) - 1):
        if times[i + 1] == times[i] + 1:
            current += 1
            if current > longest:
                longest = current
        else:
            current = 1
    # print(f"[DEBUG] get_longest_consecutive computed: {longest} for times {times}")
    return longest


def generate_scorecard(df):
    # print("[DEBUG] Generating scorecard from DataFrame:")
    # print(df)
    try:
        hand_score = 10
        one_hand_times = []
        no_hand_times = []
        both_hand_times = []

        # Debug all unique annotations
        # print("[DEBUG] Unique annotations:", df["Annotation"].unique())

        for _, row in df.iterrows():
            # Get the original annotation without lower() to match exact format
            annotation = row["Annotation"].strip()
            times = re.findall(r"Time:\s*(\d+)s", row["Details"])
            times = [int(t) for t in times]
            # print(f"[DEBUG] Processing annotation '{annotation}' with times: {times}")

            # Match exact annotation strings from the debug output
            if annotation == "One hand on the steering":
                one_hand_times.extend(times)
            elif annotation == "No hand on the steering":
                no_hand_times.extend(times)
            elif annotation == "Both hands on the steering":
                both_hand_times.extend(times)

        # print(f"[DEBUG] one_hand_times: {one_hand_times}")
        # print(f"[DEBUG] no_hand_times: {no_hand_times}")
        # print(f"[DEBUG] both_hand_times: {both_hand_times}")

        # Update scoring logic based on actual data
        if both_hand_times:
            hand_score = 10
            # print("[DEBUG] Both hands detected, starting with full score")

        if get_longest_consecutive(one_hand_times) >= 5:
            hand_score = 5
            # print("[DEBUG] One hand penalty applied")

        if get_longest_consecutive(no_hand_times) >= 5:
            hand_score = 0
            # print("[DEBUG] No hands penalty applied")

        # Similar update for seatbelt scoring
        seatbelt_score = 0
        for _, row in df.iterrows():
            annotation = row["Annotation"].strip()
            times = re.findall(r"Time:\s*(\d+)s", row["Details"])
            times = [int(t) for t in times]

            if annotation == "Correct seatbelt":
                seatbelt_score = 10
                # print("[DEBUG] Correct seatbelt detected")
            elif annotation == "Incorrect seatbelt":
                seatbelt_score = 3
                # print("[DEBUG] Incorrect seatbelt detected")
                break
            elif annotation == "No seatbelt":
                seatbelt_score = 0
                # print("[DEBUG] No seatbelt detected")
                break

        scorecard = {
            "hands_on_steering": hand_score,
            "seatbelt": seatbelt_score,
            "total": (hand_score + seatbelt_score) / 2,
        }
        # print("[DEBUG] Final scorecard generated:", scorecard)
        return scorecard

    except Exception as e:
        # print(f"Error generating scorecard: {str(e)}")
        # print(f"Full traceback:", e.__traceback__)
        return {"hands_on_steering": 0, "seatbelt": 0, "total": 0}


def predict_video_report(video_file="video_data.mp4"):
    # print("[DEBUG] Running predict_video_report on:", video_file)
    output_video, df = process_video(video_file)
    if df is not None:
        report = df.to_string(index=False)
        scorecard = generate_scorecard(df)
    else:
        report = "No detections"
        scorecard = {"hands_on_steering": 0, "seatbelt": 0, "total": 0}
    # print("[DEBUG] predict_video_report returning output video and scorecard.")
    return output_video, report, scorecard


# For testing purposes:
# if __name__ == "__main__":
#     out_video, rep, sc = predict_video_report("input/video_data_2.mp4")
#     print("[DEBUG] Final scorecard from predict_video_report:")
#     print(sc)