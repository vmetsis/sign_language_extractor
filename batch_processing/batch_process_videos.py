import argparse
import cv2
import mediapipe as mp
import numpy as np
import os
import json
from pathlib import Path
import time

# --- MediaPipe Initialization ---
mp_holistic = mp.solutions.holistic

# --- Landmark Constants (Ensure these match your web app's utils.py) ---
NUM_POSE_LANDMARKS = 33
NUM_FACE_LANDMARKS = 468
NUM_HAND_LANDMARKS = 21
POSE_FEATURES = NUM_POSE_LANDMARKS * 3  # x, y, z per landmark
FACE_FEATURES = NUM_FACE_LANDMARKS * 3
HAND_FEATURES = NUM_HAND_LANDMARKS * 3
TOTAL_FEATURES = POSE_FEATURES + FACE_FEATURES + 2 * HAND_FEATURES # 1629

# --- Landmark Extraction Function (Copied/Adapted from utils.py) ---
def extract_landmarks(results):
    """Extracts landmarks into a flat numpy array."""
    pose = np.array([[res.x, res.y, res.z] for res in results.pose_landmarks.landmark]).flatten() \
        if results.pose_landmarks else np.zeros(POSE_FEATURES)

    face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() \
        if results.face_landmarks else np.zeros(FACE_FEATURES)

    lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() \
        if results.left_hand_landmarks else np.zeros(HAND_FEATURES)

    rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() \
        if results.right_hand_landmarks else np.zeros(HAND_FEATURES)

    # Concatenate in the fixed order: Pose, Face, Left Hand, Right Hand
    combined = np.concatenate([pose, face, lh, rh])

    # Ensure the output array always has the fixed size (should be guaranteed by np.zeros)
    if len(combined) != TOTAL_FEATURES:
         print(f"  >> Warning: Landmark feature count mismatch. Expected {TOTAL_FEATURES}, got {len(combined)}. Padding/Truncating.")
         # Pad with zeros if too short
         if len(combined) < TOTAL_FEATURES:
             combined = np.pad(combined, (0, TOTAL_FEATURES - len(combined)), 'constant', constant_values=0)
         # Truncate if too long (indicates a definition issue)
         elif len(combined) > TOTAL_FEATURES:
              combined = combined[:TOTAL_FEATURES]

    return combined.tolist() # Return as list for JSON serialization

# --- Main Video Processing Function ---
def process_video(video_path: Path, output_dir: Path, holistic_model):
    """
    Processes a single video file, extracts landmarks frame by frame,
    and saves the sequence data as a JSON file.
    """
    video_name = video_path.stem # Get filename without extension
    output_json_path = output_dir / f"{video_name}.json"

    # Skip if JSON already exists
    if output_json_path.exists():
        print(f"  Skipping '{video_path.name}', JSON already exists: '{output_json_path.name}'")
        return

    sequence_data = []
    cap = cv2.VideoCapture(str(video_path)) # cv2 needs string path

    if not cap.isOpened():
        print(f"  Error: Could not open video file {video_path.name}")
        return

    frame_count = 0
    start_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break # End of video

        # Convert color BGR -> RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False # Optimize: Make read-only for MediaPipe

        # Make detection
        results = holistic_model.process(image_rgb)

        # Extract landmarks for the current frame
        landmarks = extract_landmarks(results)
        sequence_data.append(landmarks)
        frame_count += 1

    cap.release()
    end_time = time.time()
    processing_time = end_time - start_time

    if not sequence_data:
        print(f"  Warning: No landmarks extracted from {video_path.name}")
        return

    # Save the data
    try:
        with open(output_json_path, 'w') as f:
            json.dump(sequence_data, f) # Use default compact JSON format
        print(f"  Successfully processed '{video_path.name}' ({frame_count} frames) -> '{output_json_path.name}' ({processing_time:.2f}s)")
    except Exception as e:
        print(f"  Error saving data for {video_path.name} to {output_json_path}: {e}")


# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Batch process videos to extract MediaPipe Holistic landmarks.")
    parser.add_argument("--input_dir", required=True, help="Directory containing the input video files.")
    parser.add_argument("--output_dir", required=True, help="Directory where the output JSON files will be saved.")
    parser.add_argument("--min_detection_confidence", type=float, default=0.5, help="Minimum detection confidence for Holistic model.")
    parser.add_argument("--min_tracking_confidence", type=float, default=0.5, help="Minimum tracking confidence for Holistic model.")

    args = parser.parse_args()

    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)

    if not input_path.is_dir():
        print(f"Error: Input directory not found: {input_path}")
        return

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Output will be saved to: {output_path.resolve()}")

    # List of common video file extensions
    video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}

    video_files = [f for f in input_path.iterdir() if f.is_file() and f.suffix.lower() in video_extensions]

    if not video_files:
        print(f"No video files found in {input_path}")
        return

    print(f"Found {len(video_files)} video files to process.")

    # Initialize MediaPipe Holistic model ONCE
    try:
        with mp_holistic.Holistic(
            min_detection_confidence=args.min_detection_confidence,
            min_tracking_confidence=args.min_tracking_confidence
            ) as holistic:

            for video_file in video_files:
                print(f"Processing: {video_file.name}...")
                try:
                    process_video(video_file, output_path, holistic)
                except Exception as e:
                    print(f"  !! Unhandled error processing {video_file.name}: {e}")

    except Exception as e:
        print(f"Error initializing MediaPipe Holistic: {e}")
        print("Please ensure MediaPipe is installed correctly.")
        return

    print("\nBatch processing complete.")


if __name__ == "__main__":
    main()