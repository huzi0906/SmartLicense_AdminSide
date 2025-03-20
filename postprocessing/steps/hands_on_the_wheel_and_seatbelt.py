from ultralytics import YOLO
import cv2
import os
import pandas as pd
import re  # needed for scorecard processing

# Load the YOLO model
model = YOLO("steps/weights/best.pt")


def process_video(video_path):
    if not video_path:
        return None, None

    try:
        video_capture = cv2.VideoCapture(video_path)
        if not video_capture.isOpened():
            raise ValueError("Error opening video file")

        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(video_capture.get(cv2.CAP_PROP_FPS))

        output_path = "processed_output.webm"
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

            if frame_skip_counter % 4 == 0:
                results = model.predict(source=frame, verbose=False)
                if len(results[0].boxes) > 0:
                    current_detections = []
                    for result in results[0].boxes:
                        annotation = model.names[int(result.cls)]
                        annotation = annotation.replace("_", " ").capitalize()
                        confidence = float(result.conf) * 100
                        current_detections.append([annotation, second, confidence])
                    second_annotations[second] = current_detections
                    last_valid_annotations = current_detections
                elif last_valid_annotations and second not in second_annotations:
                    second_annotations[second] = last_valid_annotations
                annotated_frame = results[0].plot()
            else:
                annotated_frame = frame

            output_video.write(annotated_frame)
            frame_count += 1
            frame_skip_counter += 1

        annotations_dict = {}
        max_second = max(second_annotations.keys())

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

        video_capture.release()
        output_video.release()
        df = pd.DataFrame(detection_data, columns=["Annotation", "Details"])
        return output_path, df

    except Exception as e:
        print(f"Error processing video: {str(e)}")
        return None, None


def process_img(img):
    if img is None:
        return None
    results = model.predict(source=img, verbose=False)
    return results[0].plot()


def generate_scorecard(df):
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
        return longest

    # Hands on wheel score (out of 10)
    hand_score = 10
    hand_times = []
    for _, row in df.iterrows():
        annotation = row["Annotation"].strip().lower()
        if annotation in ["one hand", "no hand"]:
            times = re.findall(r"Time:\s*(\d+)s", row["Details"])
            hand_times.extend([int(t) for t in times])
    if get_longest_consecutive(hand_times) >= 5:
        hand_score = 10 - 5  # deduct 5

    # Seatbelt score (out of 10)
    # Check for "no seatbelt", "incorrect seatbelt" and "seatbelt".
    no_seatbelt_times = []
    incorrect_seatbelt_times = []
    correct_seatbelt_times = []
    for _, row in df.iterrows():
        annotation = row["Annotation"].strip().lower()
        times = re.findall(r"Time:\s*(\d+)s", row["Details"])
        times = [int(t) for t in times]
        if annotation == "no seatbelt":
            no_seatbelt_times.extend(times)
        elif annotation == "incorrect seatbelt":
            incorrect_seatbelt_times.extend(times)
        elif annotation == "seatbelt":
            correct_seatbelt_times.extend(times)
    if no_seatbelt_times and get_longest_consecutive(no_seatbelt_times) >= 15:
        seatbelt_score = 0
    elif incorrect_seatbelt_times:
        seatbelt_score = 3
    elif correct_seatbelt_times:
        seatbelt_score = 10
    else:
        seatbelt_score = 0

    scorecard = {
        "hands_on_wheel": hand_score,
        "seatbelt": seatbelt_score,
        "total": (hand_score + seatbelt_score) / 2,
    }
    return scorecard


def predict_video_report(video_file="video_data.mp4"):
    output_video, df = process_video(video_file)
    if df is not None:
        report = df.to_string(index=False)
        scorecard = generate_scorecard(df)
    else:
        report = "No detections"
        scorecard = {"hands_on_wheel": 0, "seatbelt": 0, "total": 0}
    # print("Video Prediction Report:")
    # print(report)
    # print("Scorecard:")
    # print(scorecard)
    return output_video, report, scorecard


# The Gradio UI has been commented out since only frame processing and reporting is required.
# Uncomment below if UI is needed.
#
# import gradio as gr
# with gr.Blocks(css="""
# #detection-data-table .wrap .label {
#     font-size: 20px !important;
# }
# """) as demo:
#     with gr.Tab("Video"):
#         with gr.Row():
#             video_input = gr.Video(label="Original Video")
#             video_output = gr.Video(label="Processed Video")
#         process_button = gr.Button("Process Video")
#         table_output = gr.DataFrame(headers=["Annotation", "Details"], elem_id="detection-data-table")
#         process_button.click(fn=process_video, inputs=video_input, outputs=[video_output, table_output])
#
#     with gr.Tab("Image"):
#         image_input = gr.Image(label="Input Image")
#         image_output = gr.Image(label="Processed Image")
#         process_button_img = gr.Button("Process Image")
#         process_button_img.click(fn=process_img, inputs=image_input, outputs=image_output)
#
# demo.launch()
