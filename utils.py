# utils.py
import cv2
import mediapipe as mp
import numpy as np
import os
import json
from datetime import datetime

# Initialize MediaPipe solutions
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

# Define the number of landmarks to extract for consistency
# Pose: 33 landmarks * 3 coordinates (x, y, z) = 99
# Face: 468 landmarks * 3 coordinates = 1404
# Left Hand: 21 landmarks * 3 coordinates = 63
# Right Hand: 21 landmarks * 3 coordinates = 63
# Total = 99 + 1404 + 63 + 63 = 1629 features per frame
NUM_POSE_LANDMARKS = 33
NUM_FACE_LANDMARKS = 468
NUM_HAND_LANDMARKS = 21
TOTAL_FEATURES = (NUM_POSE_LANDMARKS + NUM_FACE_LANDMARKS + 2 * NUM_HAND_LANDMARKS) * 3

def extract_landmarks(results):
    """Extracts landmarks into a flat numpy array."""
    pose = np.array([[res.x, res.y, res.z] for res in results.pose_landmarks.landmark]).flatten() \
        if results.pose_landmarks else np.zeros(NUM_POSE_LANDMARKS * 3)

    face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() \
        if results.face_landmarks else np.zeros(NUM_FACE_LANDMARKS * 3)

    lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() \
        if results.left_hand_landmarks else np.zeros(NUM_HAND_LANDMARKS * 3)

    rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() \
        if results.right_hand_landmarks else np.zeros(NUM_HAND_LANDMARKS * 3)

    # Ensure the output array always has the fixed size
    combined = np.concatenate([pose, face, lh, rh])

    # Double check size, though concatenation should handle it if zeros are correct length
    if len(combined) != TOTAL_FEATURES:
         # Handle error or pad/truncate if necessary, though padding with zeros handles missing parts
         # This check is more for debugging the constants NUM_..._LANDMARKS
         print(f"Warning: Landmark feature count mismatch. Expected {TOTAL_FEATURES}, got {len(combined)}")
         # Example: Pad with zeros if too short (shouldn't happen with np.zeros fallback)
         if len(combined) < TOTAL_FEATURES:
             combined = np.pad(combined, (0, TOTAL_FEATURES - len(combined)), 'constant', constant_values=0)
         # Example: Truncate if too long (indicates a definition issue)
         elif len(combined) > TOTAL_FEATURES:
              combined = combined[:TOTAL_FEATURES]


    return combined

def process_video_file(video_path, output_dir="data"):
    """Processes a video file, extracts landmarks, and saves as JSON."""
    sequence_data = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return None

    # Use Holistic model with desired confidence levels
    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break # End of video

            # Convert color BGR -> RGB
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Make detection
            results = holistic.process(image_rgb)

            # Extract landmarks for the current frame
            landmarks = extract_landmarks(results)
            sequence_data.append(landmarks.tolist()) # Append as list for JSON serialization

    cap.release()

    if not sequence_data:
        print(f"Warning: No landmarks extracted from {video_path}")
        return None

    # Save the data
    # Use filename and timestamp for uniqueness
    base_filename = os.path.splitext(os.path.basename(video_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{base_filename}_{timestamp}_landmarks.json"
    output_path = os.path.join(output_dir, output_filename)

    os.makedirs(output_dir, exist_ok=True) # Ensure output directory exists
    try:
        with open(output_path, 'w') as f:
            json.dump(sequence_data, f, indent=4)
        print(f"Landmark data saved to {output_path}")
        return output_path # Return path to saved data
    except Exception as e:
        print(f"Error saving data to {output_path}: {e}")
        return None


def process_single_frame(frame_bgr):
    """Processes a single frame (from webcam) and returns landmarks."""
    # Convert color BGR -> RGB
    image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    # Process frame (reuse holistic instance if possible for performance,
    # but for simplicity here, we create one per call. Consider optimization later)
    # NOTE: For real-time, initializing Holistic per frame is VERY INEFFICIENT.
    # It should be initialized once in the main app context. We'll adjust this in app.py.
    with mp_holistic.Holistic(static_image_mode=True, # Treat each frame independently for webcam
                              min_detection_confidence=0.5,
                              min_tracking_confidence=0.5) as holistic:
        results = holistic.process(image_rgb)
        landmarks = extract_landmarks(results)
        return landmarks.tolist() # Return as list