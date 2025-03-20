# from flask import Flask
# import subprocess

# app = Flask(__name__)

# # Raspberry Pi details
# RASPBERRY_PI_USER = "abdullah"
# RASPBERRY_PI_HOST = "192.168.100.174"
# MANAGE_SCRIPT = "/home/abdullah/Desktop/manage_server.sh"
# REMOTE_LOG_FILE = "/home/abdullah/Desktop/sensor_log.txt"
# LOCAL_LOG_FILE = "./sensor_log.txt"


# @app.route("/start", methods=["POST"])
# def start_server():
#     try:
#         # Run the start command and capture output
#         result = subprocess.run(
#             [
#                 "ssh",
#                 "-o",
#                 "ServerAliveInterval=60",  # Keep SSH alive
#                 f"{RASPBERRY_PI_USER}@{RASPBERRY_PI_HOST}",
#                 f"bash {MANAGE_SCRIPT} start",
#             ],
#             capture_output=True,
#             text=True,
#             check=True,
#         )
#         return (
#             f"Server started:\n{result.stdout}\nErrors (if any): {result.stderr}",
#             200,
#         )
#     except subprocess.CalledProcessError as e:
#         return f"Error starting server:\nStdout: {e.stdout}\nStderr: {e.stderr}", 500


# @app.route("/stop", methods=["POST"])
# def stop_server():
#     try:
#         # Stop the server
#         stop_result = subprocess.run(
#             [
#                 "ssh",
#                 f"{RASPBERRY_PI_USER}@{RASPBERRY_PI_HOST}",
#                 f"bash {MANAGE_SCRIPT} stop",
#             ],
#             capture_output=True,
#             text=True,
#             check=True,
#         )
#         # Retrieve the log file
#         scp_result = subprocess.run(
#             [
#                 "scp",
#                 f"{RASPBERRY_PI_USER}@{RASPBERRY_PI_HOST}:{REMOTE_LOG_FILE}",
#                 LOCAL_LOG_FILE,
#             ],
#             capture_output=True,
#             text=True,
#             check=True,
#         )
#         # Read the log file content for verification
#         with open(LOCAL_LOG_FILE, "r") as f:
#             log_content = f.read()
#         return (
#             f"Server stopped:\n{stop_result.stdout}\n"
#             f"Log file retrieved to {LOCAL_LOG_FILE}\n"
#             f"Log content:\n{log_content if log_content else 'Log file is empty'}\n"
#             f"Errors (if any): {stop_result.stderr or scp_result.stderr}",
#             200,
#         )
#     except subprocess.CalledProcessError as e:
#         return f"Error:\nStdout: {e.stdout}\nStderr: {e.stderr}", 500


# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)
from flask import Flask, request
import subprocess
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5013"}})

# Raspberry Pi details
RASPBERRY_PI_USER = "abdullah"
RASPBERRY_PI_HOST = "192.168.100.174"
MANAGE_SCRIPT = "/home/abdullah/Desktop/manage_server.sh"
REMOTE_LOG_FILE = "/home/abdullah/Desktop/sensor_log.txt"
LOCAL_LOG_FILE = "./sensor_log.txt"


@app.route("/start", methods=["POST"])
def start_server():
    
    try:
        # Run the start command and capture output
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "ServerAliveInterval=60",  # Keep SSH alive
                f"{RASPBERRY_PI_USER}@{RASPBERRY_PI_HOST}",
                f"bash {MANAGE_SCRIPT} start",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return (
            f"Server started:\n{result.stdout}\nErrors (if any): {result.stderr}",
            200,
        )
    except subprocess.CalledProcessError as e:
        return f"Error starting server:\nStdout: {e.stdout}\nStderr: {e.stderr}", 500


@app.route("/stop", methods=["POST"])
def stop_server():
    try:
        # Stop the server
        stop_result = subprocess.run(
            [
                "ssh",
                "-o",
                "ServerAliveInterval=60",  # Keep SSH alive
                f"{RASPBERRY_PI_USER}@{RASPBERRY_PI_HOST}",
                f"bash {MANAGE_SCRIPT} stop",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Retrieve the log file
        scp_log_result = subprocess.run(
            [
                "scp",
                f"{RASPBERRY_PI_USER}@{RASPBERRY_PI_HOST}:{REMOTE_LOG_FILE}",
                LOCAL_LOG_FILE,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Read the log file content for verification
        with open(LOCAL_LOG_FILE, "r") as f:
            log_content = f.read()

        # Retrieve video files
        try:
            scp_video_result = subprocess.run(
                [
                    "scp",
                    f"{RASPBERRY_PI_USER}@{RASPBERRY_PI_HOST}:/home/abdullah/Desktop/mobile_log_*.mp4",
                    "./",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            video_files_copied = True
            video_errors = scp_video_result.stderr
        except subprocess.CalledProcessError as e:
            video_files_copied = False
            video_errors = e.stderr

        return (
            f"Server stopped:\n{stop_result.stdout}\n"
            f"Log file retrieved to {LOCAL_LOG_FILE}\n"
            f"Log content:\n{log_content if log_content else 'Log file is empty'}\n"
            f"Video files copied: {'Yes' if video_files_copied else 'No'}\n"
            f"Video errors (if any): {video_errors}\n"
            f"Other errors (if any): {stop_result.stderr or scp_log_result.stderr}",
            200,
        )
    except subprocess.CalledProcessError as e:
        return (
            f"Error stopping server or retrieving log:\nStdout: {e.stdout}\nStderr: {e.stderr}",
            500,
        )


@app.route("/collision", methods=["POST"])
def handle_collision():
    """Handle collision detection from Raspberry Pi by stopping the script and retrieving the log."""
    return stop_server()  # Reuse the stop_server logic


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
