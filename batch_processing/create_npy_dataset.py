import argparse
import json
import numpy as np
from pathlib import Path
import sys

# --- Landmark Constants (MUST match the extraction script exactly!) ---
# These define the structure of the features within each frame's flat array.
NUM_POSE_LANDMARKS = 33
NUM_FACE_LANDMARKS = 468
NUM_HAND_LANDMARKS = 21

POSE_FEATURES = NUM_POSE_LANDMARKS * 3  # 99 (x, y, z)
FACE_FEATURES = NUM_FACE_LANDMARKS * 3  # 1404
HAND_FEATURES = NUM_HAND_LANDMARKS * 3  # 63

# Calculate start and end indices for each landmark type in the flat array
# Order: Pose, Face, Left Hand, Right Hand
POSE_START, POSE_END = 0, POSE_FEATURES
FACE_START, FACE_END = POSE_END, POSE_END + FACE_FEATURES
LH_START, LH_END = FACE_END, FACE_END + HAND_FEATURES
RH_START, RH_END = LH_END, LH_END + HAND_FEATURES

TOTAL_FEATURES_EXPECTED = RH_END # Should be 1629

# Dictionary mapping landmark type names to their slice indices and feature count
LANDMARK_INFO = {
    "Pose": {"slice": slice(POSE_START, POSE_END), "features": POSE_FEATURES},
    "Face": {"slice": slice(FACE_START, FACE_END), "features": FACE_FEATURES},
    "LeftHand": {"slice": slice(LH_START, LH_END), "features": HAND_FEATURES},
    "RightHand": {"slice": slice(RH_START, RH_END), "features": HAND_FEATURES},
}

# --- Main Function ---
def main():
    parser = argparse.ArgumentParser(description="Load landmark JSON files, select features, pad/truncate sequences, and save as a NumPy array.")
    parser.add_argument("--input_dir", required=True, help="Directory containing the input JSON landmark files.")
    parser.add_argument("--output_file", required=True, help="Path to save the output .npy file.")
    parser.add_argument("--landmarks", required=True, nargs='+', choices=LANDMARK_INFO.keys(),
                        help=f"Which landmarks to include. Choose one or more from: {list(LANDMARK_INFO.keys())}")
    parser.add_argument("--max_len", required=True, type=int, help="Maximum sequence length (number of frames). Shorter sequences will be padded, longer ones truncated.")

    args = parser.parse_args()

    input_path = Path(args.input_dir)
    output_path = Path(args.output_file)
    selected_landmark_names = args.landmarks
    max_len = args.max_len

    if not input_path.is_dir():
        print(f"Error: Input directory not found: {input_path}")
        sys.exit(1)

    if max_len <= 0:
        print(f"Error: --max_len must be a positive integer.")
        sys.exit(1)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Determine selected features ---
    selected_slices = []
    total_selected_features = 0
    print("Selected Landmarks:")
    for name in selected_landmark_names:
        info = LANDMARK_INFO[name]
        selected_slices.append(info["slice"])
        total_selected_features += info["features"]
        print(f"- {name} ({info['features']} features, indices {info['slice'].start}-{info['slice'].stop-1})")

    if total_selected_features == 0:
        print("Error: No features selected based on landmark choices.")
        sys.exit(1)
    print(f"Total selected features per frame: {total_selected_features}")

    # --- Find and process JSON files ---
    json_files = sorted(list(input_path.glob('*.json'))) # Sort for consistency
    if not json_files:
        print(f"Error: No JSON files found in {input_path}")
        sys.exit(1)

    print(f"\nFound {len(json_files)} JSON files to process.")

    all_processed_sequences = []

    for i, json_file in enumerate(json_files):
        print(f"Processing ({i+1}/{len(json_files)}): {json_file.name}...")
        try:
            with open(json_file, 'r') as f:
                # Load the sequence data (list of frame lists)
                sequence_data = json.load(f)

            if not isinstance(sequence_data, list) or not sequence_data:
                print(f"  Warning: Skipping empty or invalid JSON file: {json_file.name}")
                continue

            # Convert to NumPy array for easier slicing
            sequence_array = np.array(sequence_data, dtype=np.float32) # Use float32

            # Verify feature count in the first frame
            if sequence_array.shape[1] != TOTAL_FEATURES_EXPECTED:
                 print(f"  Warning: Skipping {json_file.name}. Unexpected number of features per frame. Expected {TOTAL_FEATURES_EXPECTED}, found {sequence_array.shape[1]}.")
                 continue

            # Select the specified landmark features (columns)
            selected_features_sequence = np.concatenate(
                [sequence_array[:, s] for s in selected_slices], axis=1
            )
            # Assert shape is (num_frames, total_selected_features)
            assert selected_features_sequence.shape[1] == total_selected_features, \
                f"Feature selection error for {json_file.name}"


            # --- Pad or Truncate Sequence Length ---
            num_frames = selected_features_sequence.shape[0]
            processed_sequence = np.zeros((max_len, total_selected_features), dtype=np.float32)

            if num_frames == max_len:
                processed_sequence = selected_features_sequence
                print(f"  Sequence length matches max_len ({num_frames} frames).")
            elif num_frames > max_len:
                # Truncate
                processed_sequence = selected_features_sequence[:max_len, :]
                print(f"  Truncated sequence from {num_frames} to {max_len} frames.")
            else: # num_frames < max_len
                # Pad with zeros at the end
                processed_sequence[:num_frames, :] = selected_features_sequence
                print(f"  Padded sequence from {num_frames} to {max_len} frames.")

            all_processed_sequences.append(processed_sequence)

        except json.JSONDecodeError:
            print(f"  Error: Could not decode JSON from file: {json_file.name}")
        except Exception as e:
            print(f"  Error processing file {json_file.name}: {e}")

    if not all_processed_sequences:
        print("\nError: No valid sequences were processed. Output file will not be created.")
        sys.exit(1)

    # --- Stack sequences into a 3D NumPy array ---
    # Shape: (num_instances, max_len, total_selected_features)
    final_dataset = np.stack(all_processed_sequences, axis=0)

    print(f"\nSuccessfully processed {len(all_processed_sequences)} sequences.")
    print(f"Final dataset shape: {final_dataset.shape}")

    # --- Save the dataset ---
    try:
        np.save(output_path, final_dataset)
        print(f"Dataset saved successfully to: {output_path.resolve()}")
    except Exception as e:
        print(f"Error saving NumPy array to {output_path}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()