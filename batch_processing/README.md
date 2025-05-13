# MediaPipe Landmark Batch Extraction Script

This script batch processes video files containing human motion (e.g., sign language performances) using Google's MediaPipe framework to extract detailed landmark information (pose, face, hands) for each frame. The extracted data is saved as a JSON file for each video, suitable for further analysis or training machine learning models.

## Overview

The script iterates through all video files (common formats like `.mp4`, `.avi`, `.mov`, etc.) found in a specified input directory. For each video, it uses the MediaPipe Holistic solution to detect and track landmarks frame-by-frame. The extracted landmark coordinates (x, y, z) for each frame are flattened into a single list and stored sequentially. The resulting time series data for the entire video is saved as a JSON file in a specified output directory. The output JSON filename matches the input video filename (e.g., `sign_video_1.mp4` -> `sign_video_1.json`).

## Requirements

*   Python 3.8+
*   Required Python packages:
    *   `opencv-python` (for video reading)
    *   `mediapipe` (for landmark extraction)
    *   `numpy` (for numerical operations)

## Installation

1.  Clone or download the script (`batch_process_videos.py`).
2.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
    (Make sure `requirements.txt` is in your current directory or provide the correct path).

## Usage

Run the script from your terminal using the following command structure:

```bash
python batch_process_videos.py --input_dir <path_to_your_videos> --output_dir <path_to_save_json> [options]
```

**Arguments:**

*   `--input_dir` (Required): Path to the directory containing the video files you want to process.
*   `--output_dir` (Required): Path to the directory where the output JSON files will be saved. The directory will be created if it doesn't exist.
*   `--min_detection_confidence` (Optional): Minimum confidence value ([0.0, 1.0]) for the person detection to be considered successful. Default: `0.5`.
*   `--min_tracking_confidence` (Optional): Minimum confidence value ([0.0, 1.0]) for the landmarks to be considered tracked successfully. Default: `0.5`.

**Example:**

```bash
python batch_process_videos.py --input_dir ./my_sign_videos --output_dir ./landmark_data --min_detection_confidence 0.6
```

This command will process all videos in the `./my_sign_videos` directory and save the corresponding JSON landmark files into the `./landmark_data` directory, using a detection confidence of 0.6.

## Output JSON File Structure

For each input video (e.g., `example.mp4`), a corresponding JSON file (e.g., `example.json`) is created in the output directory.

The structure of each JSON file is as follows:

1.  **Top Level:** A JSON Array (`[]`).
2.  **Elements:** Each element in the top-level array represents a single frame from the video, ordered sequentially.
3.  **Frame Data:** Each frame element is itself a JSON Array (`[]`) containing a flat list of floating-point numbers representing the landmark coordinates.
4.  **Landmark Order & Feature Count:**
    *   The array for each frame contains exactly **1629** numerical features.
    *   These features represent the concatenated x, y, and z coordinates of all extracted landmarks in a fixed order:
        *   **Pose Landmarks (Indices 0 - 98):**
            *   33 landmarks (`mp_holistic.POSE_LANDMARKS`)
            *   3 coordinates each (x, y, z)
            *   Total: 33 * 3 = 99 features
            *   Format: `[pose0_x, pose0_y, pose0_z, pose1_x, ..., pose32_z]`
        *   **Face Landmarks (Indices 99 - 1502):**
            *   468 landmarks (`mp_holistic.FACEMESH_TESSELATION`)
            *   3 coordinates each (x, y, z)
            *   Total: 468 * 3 = 1404 features
            *   Format: `[face0_x, face0_y, face0_z, face1_x, ..., face467_z]`
        *   **Left Hand Landmarks (Indices 1503 - 1565):**
            *   21 landmarks (`mp_holistic.HAND_CONNECTIONS`)
            *   3 coordinates each (x, y, z)
            *   Total: 21 * 3 = 63 features
            *   Format: `[leftHand0_x, leftHand0_y, leftHand0_z, ..., leftHand20_z]`
        *   **Right Hand Landmarks (Indices 1566 - 1628):**
            *   21 landmarks (`mp_holistic.HAND_CONNECTIONS`)
            *   3 coordinates each (x, y, z)
            *   Total: 21 * 3 = 63 features
            *   Format: `[rightHand0_x, rightHand0_y, rightHand0_z, ..., rightHand20_z]`
    *   **Total Features per Frame = 99 (Pose) + 1404 (Face) + 63 (Left Hand) + 63 (Right Hand) = 1629**

5.  **Missing Landmarks:** If MediaPipe fails to detect a component (e.g., hands are out of view), the corresponding section in the feature array for that frame will be filled entirely with **zeros** (`0.0`). This ensures every frame array always has 1629 elements.

6.  **Coordinate System:**
    *   `x`, `y`: Landmark coordinates normalized to `[0.0, 1.0]` based on the video frame's width and height. (0,0) is typically the top-left corner.
    *   `z`: Represents depth relative to the approximate center of the hips. Smaller values are closer to the camera. The magnitude is roughly proportional to the scale of the `x` coordinate.

**Conceptual Example (`example.json`):**

```json
[
  // Frame 0
  [0.51, 0.32, -0.85, ..., 0.65, 0.88, -0.21,  // 99 pose values
   0.50, 0.25, -0.05, ..., 0.49, 0.22, 0.01,  // 1404 face values
   0.21, 0.45, -0.15, ..., 0.18, 0.55, -0.05,  // 63 left hand values (if detected)
   0.0, 0.0, 0.0, ..., 0.0, 0.0, 0.0           // 63 right hand values (if not detected)
  ],
  // Frame 1
  [0.52, 0.33, -0.84, ..., 0.66, 0.89, -0.20,  // Pose
   0.51, 0.26, -0.04, ..., 0.50, 0.23, 0.02,  // Face
   0.22, 0.46, -0.14, ..., 0.19, 0.56, -0.04,  // Left Hand
   0.0, 0.0, 0.0, ..., 0.0, 0.0, 0.0           // Right Hand
  ],
  // ... more frames
]
```

## Future Use

The generated JSON files provide a structured time-series representation of the motion capture data. This format is well-suited as input for training deep learning models, such as LSTMs, GRUs, Transformers, or Temporal Convolutional Networks (TCNs), for tasks like isolated sign language recognition or gesture classification. The fixed feature length per frame simplifies data loading and batching.

## Loading the JSON Data into a Numpy Array
To load the JSON data into a Numpy array for further processing or model training, you can use the following script:

```bash
# To load only hand data, pad/truncate to 100 frames, and save:
python create_npy_dataset.py \
    --input_dir ./landmark_data \
    --output_file ./datasets/hands_only_len100.npy \
    --landmarks LeftHand RightHand \
    --max_len 100
```
This command will create a Numpy array with the specified landmarks, padded or truncated to 100 frames, and save it as `hands_only_len100.npy` in the `./datasets` directory.