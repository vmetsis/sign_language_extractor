// static/js/playback.js

// Use 'load' event listener to wait for ALL resources
window.addEventListener('load', () => {
    console.log("Window loaded. Initializing playback script.");

    // --- DOM Elements ---
    const jsonFileInput = document.getElementById('jsonFile');
    const playbackCanvas = document.getElementById('playbackCanvas');
    const canvasCtx = playbackCanvas.getContext('2d'); // Get context once
    const playButton = document.getElementById('playButton');
    const pauseButton = document.getElementById('pauseButton');
    const stopButton = document.getElementById('stopButton');
    const speedControl = document.getElementById('speedControl');
    const playbackStatus = document.getElementById('playbackStatus');
    const frameIndicator = document.getElementById('frameIndicator');

    // --- Playback State ---
    let landmarkFrames = [];
    let currentFrameIndex = 0;
    let isPlaying = false;
    let animationTimeoutId = null;
    let baseFrameMillis = 1000 / 30;

    // Constants (Keep these)
    const POSE_LANDMARKS = 33;
    const FACE_LANDMARKS = 468;
    const HAND_LANDMARKS = 21;
    const POSE_FEATURES = POSE_LANDMARKS * 3;
    const FACE_FEATURES = FACE_LANDMARKS * 3;
    const HAND_FEATURES = HAND_LANDMARKS * 3;
    const TOTAL_FEATURES = POSE_FEATURES + FACE_FEATURES + 2 * HAND_FEATURES;

    const POSE_START = 0;
    const FACE_START = POSE_FEATURES;
    const LH_START = FACE_START + FACE_FEATURES;
    const RH_START = LH_START + HAND_FEATURES;

    // --- File Loading ---
    // (Keep the jsonFileInput event listener exactly as it was)
    jsonFileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) { playbackStatus.textContent = 'No file selected.'; return; }
        if (!file.name.endsWith('.json')) {
             playbackStatus.textContent = 'Error: Please select a .json file.'; landmarkFrames = []; resetPlayback(); return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            console.log("FileReader onload triggered.");
            try {
                console.log("Attempting to parse JSON...");
                const content = e.target.result; landmarkFrames = JSON.parse(content); console.log(`Parsed ${landmarkFrames.length} frames.`);
                if (!Array.isArray(landmarkFrames) || landmarkFrames.length === 0) { throw new Error("Invalid JSON format or empty data."); }
                if (!Array.isArray(landmarkFrames[0]) || landmarkFrames[0].length !== TOTAL_FEATURES) { throw new Error(`Invalid data structure in frame 0. Expected ${TOTAL_FEATURES} features, found ${landmarkFrames[0]?.length}.`); }
                console.log("Parsing and validation successful."); playbackStatus.textContent = `Loaded ${landmarkFrames.length} frames from ${file.name}.`;
                resetPlayback(); drawFrame(currentFrameIndex);
                if (landmarkFrames.length > 0) {
                    if (playbackStatus.textContent.startsWith("Error: Playback libraries")) { playButton.disabled = true; } else { playButton.disabled = false; }
                } else { playButton.disabled = true; }
            } catch (error) {
                console.error("Error inside onload try-catch:", error); playbackStatus.textContent = `Error loading file: ${error.message}`; landmarkFrames = []; resetPlayback();
            }
        };
        reader.onerror = (e) => {
            console.error("FileReader onerror triggered:", e); playbackStatus.textContent = 'Error reading file.'; landmarkFrames = []; resetPlayback();
        };
        reader.readAsText(file);
    });

    // --- Landmark Reconstruction ---
    // (Keep the reconstructLandmarks function exactly as it was)
    function reconstructLandmarks(flatFrameData) {
        if (!flatFrameData || flatFrameData.length !== TOTAL_FEATURES) {
            console.warn("Invalid or missing frame data for reconstruction.");
            return { poseLandmarks: null, faceLandmarks: null, leftHandLandmarks: null, rightHandLandmarks: null };
        }
        const results = { poseLandmarks: null, faceLandmarks: null, leftHandLandmarks: null, rightHandLandmarks: null };
        const parseSlice = (start, count) => {
            const landmarks = []; let hasData = false;
            for (let i = 0; i < count; i++) {
                const idx = start + i * 3; const landmark = { x: flatFrameData[idx], y: flatFrameData[idx + 1], z: flatFrameData[idx + 2], };
                if (landmark.x !== 0 || landmark.y !== 0 || landmark.z !== 0) { hasData = true; } landmarks.push(landmark);
            } return hasData ? { landmark: landmarks } : null;
        };
        results.poseLandmarks = parseSlice(POSE_START, POSE_LANDMARKS);
        results.faceLandmarks = parseSlice(FACE_START, FACE_LANDMARKS);
        results.leftHandLandmarks = parseSlice(LH_START, HAND_LANDMARKS);
        results.rightHandLandmarks = parseSlice(RH_START, HAND_LANDMARKS);
        return results;
    }


    // --- Drawing (MODIFIED) ---
    function drawFrame(index) {
        // Check for required global functions and Holistic object
        if (typeof window.drawConnectors !== 'function' ||
            typeof window.drawLandmarks !== 'function' ||
            !window.Holistic) {
             console.error("drawFrame Error: Required drawing functions or Holistic not available!");
             playbackStatus.textContent = "Error: Playback libraries failed to load correctly. Cannot draw.";
             if(isPlaying) stop();
             return;
        }
        // We need access to Holistic constants
        const Holistic = window.Holistic;

        if (index < 0 || index >= landmarkFrames.length) {
            console.warn("Attempted to draw invalid frame index:", index);
            return;
        }

        const frameData = landmarkFrames[index];
        const reconstructed = reconstructLandmarks(frameData);

        // Clear canvas
        canvasCtx.save();
        canvasCtx.clearRect(0, 0, playbackCanvas.width, playbackCanvas.height);

        // Define drawing styles
        const landmarkRadius = 2; // << Smaller radius for landmarks
        const connectionThickness = 2; // << Consistent thickness for connections

        // --- Draw Components using GLOBAL functions ---
        try {
            // POSE
            if (reconstructed.poseLandmarks) {
                 window.drawConnectors(canvasCtx, reconstructed.poseLandmarks.landmark, Holistic.POSE_CONNECTIONS,
                                      { color: '#42A5F5', lineWidth: connectionThickness }); // Light Blue connections
                 window.drawLandmarks(canvasCtx, reconstructed.poseLandmarks.landmark,
                                     { color: '#0D47A1', radius: landmarkRadius }); // Dark Blue landmarks
            }

            // FACE (Subtle grey connections, no landmarks by default)
             if (reconstructed.faceLandmarks) {
                window.drawConnectors(canvasCtx, reconstructed.faceLandmarks.landmark, Holistic.FACEMESH_FACE_OVAL,
                                      { color: '#C0C0C0', lineWidth: 1 }); // Thin grey oval
                window.drawConnectors(canvasCtx, reconstructed.faceLandmarks.landmark, Holistic.FACEMESH_LIPS,
                                      { color: '#C0C0C0', lineWidth: 1 }); // Thin grey lips
                // Keep eye/brow connections distinct if desired, or make grey
                window.drawConnectors(canvasCtx, reconstructed.faceLandmarks.landmark, Holistic.FACEMESH_LEFT_EYE, { color: '#30FF30', lineWidth: 1 });
                window.drawConnectors(canvasCtx, reconstructed.faceLandmarks.landmark, Holistic.FACEMESH_LEFT_EYEBROW, { color: '#30FF30', lineWidth: 1 });
                window.drawConnectors(canvasCtx, reconstructed.faceLandmarks.landmark, Holistic.FACEMESH_RIGHT_EYE, { color: '#FF3030', lineWidth: 1 });
                window.drawConnectors(canvasCtx, reconstructed.faceLandmarks.landmark, Holistic.FACEMESH_RIGHT_EYEBROW, { color: '#FF3030', lineWidth: 1 });
                // Optionally draw face landmarks if needed (can be very dense)
                // window.drawLandmarks(canvasCtx, reconstructed.faceLandmarks.landmark, { color: '#808080', radius: 1 });
             }

            // LEFT HAND
            if (reconstructed.leftHandLandmarks) {
                window.drawConnectors(canvasCtx, reconstructed.leftHandLandmarks.landmark, Holistic.HAND_CONNECTIONS,
                                      { color: '#FF8A65', lineWidth: connectionThickness }); // Orange connections
                window.drawLandmarks(canvasCtx, reconstructed.leftHandLandmarks.landmark,
                                     { color: '#E65100', radius: landmarkRadius }); // Dark Orange landmarks
            }
            // RIGHT HAND
            if (reconstructed.rightHandLandmarks) {
                window.drawConnectors(canvasCtx, reconstructed.rightHandLandmarks.landmark, Holistic.HAND_CONNECTIONS,
                                      { color: '#4DD0E1', lineWidth: connectionThickness }); // Cyan connections
                window.drawLandmarks(canvasCtx, reconstructed.rightHandLandmarks.landmark,
                                     { color: '#006064', radius: landmarkRadius }); // Dark Cyan landmarks
            }
        } catch (drawError) {
             console.error("Error during drawing:", drawError);
             playbackStatus.textContent = `Error during drawing: ${drawError.message}`;
             if(isPlaying) stop();
        }

        canvasCtx.restore();
        frameIndicator.textContent = `Frame: ${index + 1} / ${landmarkFrames.length}`;
    }


    // --- Playback Controls ---
    // (Keep play, pause, stop, resetPlayback functions exactly as they were)
    function play() {
        if (isPlaying || landmarkFrames.length === 0) return;
        if (typeof window.drawConnectors !== 'function' || typeof window.drawLandmarks !== 'function' || !window.Holistic) {
             console.error("Play Error: Required drawing functions or Holistic not available!"); playbackStatus.textContent = "Error: Playback libraries failed to load. Cannot play."; return;
         }
        isPlaying = true; playButton.disabled = true; pauseButton.disabled = false; stopButton.disabled = false; jsonFileInput.disabled = true;
        function animate() {
            if (!isPlaying) return; drawFrame(currentFrameIndex); currentFrameIndex++;
            if (currentFrameIndex >= landmarkFrames.length) { stop(); } else { animationTimeoutId = setTimeout(animate, baseFrameMillis / parseFloat(speedControl.value)); }
        }
        console.log("Starting playback animation loop."); animate();
    }
    function pause() { if (!isPlaying) return; console.log("Pausing playback."); isPlaying = false; clearTimeout(animationTimeoutId); animationTimeoutId = null; playButton.disabled = false; pauseButton.disabled = true; }
    function stop() { console.log("Stopping playback."); isPlaying = false; clearTimeout(animationTimeoutId); animationTimeoutId = null; currentFrameIndex = 0; resetPlayback(); jsonFileInput.disabled = false; }
    function resetPlayback() {
        console.log("Resetting playback state."); isPlaying = false; clearTimeout(animationTimeoutId); animationTimeoutId = null; currentFrameIndex = 0; playButton.disabled = true; pauseButton.disabled = true; stopButton.disabled = true; jsonFileInput.disabled = false;
        if (landmarkFrames.length > 0) {
             drawFrame(0); if (!playbackStatus.textContent.startsWith("Error: Playback libraries")) { playButton.disabled = false; }
        } else {
             canvasCtx.clearRect(0, 0, playbackCanvas.width, playbackCanvas.height); frameIndicator.textContent = 'Frame: - / -';
        }
     }

    // --- Event Listeners ---
    playButton.addEventListener('click', play);
    pauseButton.addEventListener('click', pause);
    stopButton.addEventListener('click', stop);

    // --- Initial State ---
    playbackStatus.textContent = 'Initializing... Please select a JSON landmark file.';
    resetPlayback();
    console.log("Playback script initialization complete.");

}); // End window.addEventListener('load')