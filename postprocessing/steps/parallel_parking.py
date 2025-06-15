import re
import os

def evaluate_parallel_parking(log_file):
    complete_entries = []
    current_timestamp = None
    current_sensors = {}
    skip_timestamp = False

    with open(log_file, "r") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            match = re.match(
                r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (\d+) - (.+?)(?:\s+cm)?$",
                line,
            )
            if match:
                timestamp, sensor_id, distance = match.groups()
                sensor_id = int(sensor_id)
                if sensor_id not in [1, 2, 5, 6]:
                    continue
                if distance == "Measurement Error":
                    skip_timestamp = True
                    continue
                try:
                    distance = float(distance)
                except ValueError:
                    continue
                if timestamp != current_timestamp:
                    if (
                        current_timestamp
                        and (not skip_timestamp)
                        and len(current_sensors) >= 3
                    ):
                        # Fill missing sensor using its pair
                        expected = {1, 2, 5, 6}
                        missing = expected - current_sensors.keys()
                        for m in missing:
                            if m in [1, 2]:
                                current_sensors[m] = current_sensors.get(2 if m == 1 else 1, 0)
                            else:
                                current_sensors[m] = current_sensors.get(6 if m == 5 else 5, 0)
                        complete_entries.append((current_timestamp, current_sensors.copy()))
                    current_timestamp = timestamp
                    current_sensors = {}
                    skip_timestamp = False
                current_sensors[sensor_id] = distance

        if current_timestamp and (not skip_timestamp) and len(current_sensors) >= 3:
            expected = {1, 2, 5, 6}
            missing = expected - current_sensors.keys()
            for m in missing:
                if m in [1, 2]:
                    current_sensors[m] = current_sensors.get(2 if m == 1 else 1, 0)
                else:
                    current_sensors[m] = current_sensors.get(6 if m == 5 else 5, 0)
            complete_entries.append((current_timestamp, current_sensors.copy()))

    if len(complete_entries) < 2:
        return None, "Not enough complete data (need at least two timestamps with 3-4 sensors)"

    last_two = complete_entries[-2:]
    front_avgs, rear_avgs = [], []

    for _, sensors in last_two:
        front_avg = (sensors[5] + sensors[6]) / 2
        rear_avg = (sensors[1] + sensors[2]) / 2
        front_avgs.append(front_avg)
        rear_avgs.append(rear_avg)

    overall_front = sum(front_avgs) / len(front_avgs)
    overall_rear = sum(rear_avgs) / len(rear_avgs)

    if overall_rear == 0:
        percentage_difference = 0 if overall_front == 0 else 100
    else:
        percentage_difference = (
            abs(overall_front - overall_rear) / overall_rear
        ) * 100

    if percentage_difference < 5:
        score = 10
    elif percentage_difference < 15:
        score = 9
    elif percentage_difference < 25:
        score = 8
    elif percentage_difference < 35:
        score = 7
    elif percentage_difference < 45:
        score = 6
    elif percentage_difference < 55:
        score = 5
    elif percentage_difference < 65:
        score = 4
    elif percentage_difference < 75:
        score = 3
    elif percentage_difference < 85:
        score = 2
    else:
        score = 1

    evaluation_details = {
        "timestamps": last_two,
        "front_averages": front_avgs,
        "rear_averages": rear_avgs,
        "overall_front_avg": overall_front,
        "overall_rear_avg": overall_rear,
        "percentage_difference": percentage_difference,
        "score": score,
    }

    return score, evaluation_details

# if __name__ == "__main__":
#     log_file = "sensor_log_test.txt"
#     score, details = evaluate_parallel_parking(log_file)
#     if score is None:
#         print(details)
#     else:
#         print(f"Score: {score}/10")
#         print(f"Details: {details}")

if __name__ == "__main__":
    # Get the directory of the current script
    # current_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct path to sensor log file relative to current script
    # log_file = os.path.join(current_dir, "sensor_log_test.txt")
    log_file = "sensor_log.txt"
    score, details = evaluate_parallel_parking(log_file)
    if score is None:
        print(details)
    else:
        print(f"Score: {score}/10")
        print(f"Details: {details}")