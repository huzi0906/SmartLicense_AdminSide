import re


def evaluate_parking(log_file):
    """
    Evaluates parking based on sensor readings from the last two timestamps.
    Returns a tuple of (score, evaluation_details) or (None, error_message) if there's an error.
    """
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
                if sensor_id not in [1, 2, 3, 4]:
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
                        if len(current_sensors) == 3:
                            missing_sensor = list(
                                set([1, 2, 3, 4]) - set(current_sensors.keys())
                            )[0]
                            if missing_sensor in [1, 3]:
                                opposite = 3 if missing_sensor == 1 else 1
                                current_sensors[missing_sensor] = current_sensors[
                                    opposite
                                ]
                            else:
                                opposite = 4 if missing_sensor == 2 else 2
                                current_sensors[missing_sensor] = current_sensors[
                                    opposite
                                ]
                        complete_entries.append(
                            (current_timestamp, current_sensors.copy())
                        )
                    current_timestamp = timestamp
                    current_sensors = {}
                    skip_timestamp = False
                current_sensors[sensor_id] = distance
        if current_timestamp and (not skip_timestamp) and len(current_sensors) >= 3:
            if len(current_sensors) == 3:
                missing_sensor = list(set([1, 2, 3, 4]) - set(current_sensors.keys()))[
                    0
                ]
                if missing_sensor in [1, 3]:
                    opposite = 3 if missing_sensor == 1 else 1
                    current_sensors[missing_sensor] = current_sensors[opposite]
                else:
                    opposite = 4 if missing_sensor == 2 else 2
                    current_sensors[missing_sensor] = current_sensors[opposite]
            complete_entries.append((current_timestamp, current_sensors.copy()))

    if len(complete_entries) < 2:
        return (
            None,
            "Not enough complete data (need at least two timestamps with 3-4 sensors)",
        )

    last_two = complete_entries[-2:]
    left_avgs = []
    right_avgs = []
    for timestamp, sensors in last_two:
        left_avg = (sensors[1] + sensors[3]) / 2
        right_avg = (sensors[2] + sensors[4]) / 2
        left_avgs.append(left_avg)
        right_avgs.append(right_avg)
    overall_left_avg = sum(left_avgs) / len(left_avgs)
    overall_right_avg = sum(right_avgs) / len(right_avgs)
    if overall_left_avg == 0:
        percentage_difference = 0 if overall_right_avg == 0 else 100
    else:
        percentage_difference = (
            (
                max(overall_left_avg, overall_right_avg)
                - min(overall_left_avg, overall_right_avg)
            )
            / overall_left_avg
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
        "left_averages": left_avgs,
        "right_averages": right_avgs,
        "overall_left_avg": overall_left_avg,
        "overall_right_avg": overall_right_avg,
        "percentage_difference": percentage_difference,
        "score": score,
    }
    return score, evaluation_details


if __name__ == "__main__":
    log_file = "sensor_log.txt"
    score, details = evaluate_parking(log_file)
    if score is None:
        print(details)
    else:
        print(f"Score: {score}/10")
        print(f"Details: {details}")
