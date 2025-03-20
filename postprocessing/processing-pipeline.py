import os
from steps.reverse_parking import evaluate_parking
from steps.hands_on_the_wheel_and_seatbelt import predict_video_report


def run_pipeline():
    score, _ = evaluate_parking("steps/sensor_log.txt")
    if score is None:
        return {"error": "Reverse parking evaluation failed."}

    _, _, hands_scorecard = predict_video_report("steps/video_data.mp4")
    final_scorecard = {
        "reverse_parking_score": score,
        "hands_on_steering_score": hands_scorecard.get("hands_on_wheel", 0),
        "seatbelt_score": hands_scorecard.get("seatbelt", 0),
    }
    return final_scorecard


if __name__ == "__main__":
    final_scorecard = run_pipeline()
    print("Final Scorecard:")
    print(final_scorecard)
