# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import os
import cv2
import numpy as np
import base64
from utils import process_video_file, extract_landmarks # Import our functions
import mediapipe as mp # Import mediapipe here to initialize holistic once

# --- Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key!' # Change this!
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max upload size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True) # Ensure data directory exists

# Initialize SocketIO
# Use eventlet or gevent for better performance with WebSockets
# Try eventlet first, if issues, switch to gevent (install if needed)
socketio = SocketIO(app, async_mode='eventlet')

# Initialize MediaPipe Holistic Model ONCE
mp_holistic = mp.solutions.holistic
holistic_model = mp_holistic.Holistic(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# --- Routes ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    """Handles video file uploads and processes them."""
    if 'video' not in request.files:
        return jsonify({"error": "No video file part"}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = file.filename # Consider sanitizing filename
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(video_path)
            print(f"File saved to {video_path}")

            # Process the video using the utility function
            output_path = process_video_file(video_path, output_dir="data")

            # Clean up the uploaded file
            os.remove(video_path)

            if output_path:
                 # Instead of sending data back, let's send the path where it's saved
                 # Or potentially read the file and send its content if small enough
                return jsonify({
                    "message": "Video processed successfully!",
                    "data_path": output_path,
                    "filename": os.path.basename(output_path)
                }), 200
            else:
                return jsonify({"error": "Failed to process video or extract landmarks"}), 500

        except Exception as e:
            # Clean up if error occurs during processing
            if os.path.exists(video_path):
                os.remove(video_path)
            print(f"Error during upload/processing: {e}")
            return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    return jsonify({"error": "Invalid file"}), 400

# Serve saved data files
@app.route('/data/<filename>')
def serve_data(filename):
    try:
        return send_from_directory('data', filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

# --- Playback motion tracking JSON files ---
@app.route('/playback')
def playback():
    """Serves the playback HTML page."""
    return render_template('playback.html')


# --- SocketIO Events for Webcam ---
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('process_frame')
def handle_process_frame(data):
    """Receives a frame from the client, processes it, sends landmarks back."""
    try:
        # Decode the base64 image data
        img_data = base64.b64decode(data.split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            print("Warning: Received empty frame")
            emit('frame_result', {'landmarks': [], 'error': 'Empty frame received'})
            return

        # Convert color BGR -> RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False # To improve performance

        # Make detection using the pre-initialized model
        results = holistic_model.process(image_rgb)

        image_rgb.flags.writeable = True # Make writeable again if needed for drawing (optional)

        # Extract landmarks using the utility function
        landmarks = extract_landmarks(results)

        # Send landmarks back to the client
        emit('frame_result', {'landmarks': landmarks.tolist()}) # Send as list

    except Exception as e:
        print(f"Error processing frame: {e}")
        emit('frame_result', {'landmarks': [], 'error': str(e)})


# --- Main Execution ---
if __name__ == '__main__':
    print("Starting Flask server with SocketIO support...")
    # Use socketio.run for development; includes debug and reloader
    # Eventlet is often preferred for production SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)