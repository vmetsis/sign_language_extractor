// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Globals ---
    const socket = io();
    let videoStream = null; // Holds the MediaStream object
    let processingInterval = null; // Holds the setInterval ID
    let collectedLandmarks = [];
    const frameRate = 15; // FPS

    // --- DOM Elements ---
    // (Keep all your existing getElementById calls here)
    const uploadForm = document.getElementById('uploadForm');
    const videoFile = document.getElementById('videoFile');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadResultsArea = document.getElementById('uploadResultsArea');
    const uploadResultData = document.getElementById('uploadResultData');
    const downloadLink = document.getElementById('downloadLink');

    const webcamFeed = document.getElementById('webcamFeed');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const status = document.getElementById('status');
    const resultsArea = document.getElementById('resultsArea');
    const frameCount = document.getElementById('frameCount');
    const webcamDownloadLink = document.getElementById('webcamDownloadLink');

    // --- File Upload Logic ---
    // (Keep your existing uploadForm event listener here)
    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        uploadStatus.textContent = 'Uploading and processing...';
        uploadResultsArea.classList.add('hidden');
        downloadLink.style.display = 'none'; // Use style.display

        const formData = new FormData();
        formData.append('video', videoFile.files[0]);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (response.ok) {
                uploadStatus.textContent = `Success: ${result.message}`;
                uploadResultData.textContent = `Data saved on server as: ${result.filename}\nClick link to download.`;
                downloadLink.href = `/data/${result.filename}`;
                downloadLink.download = result.filename;
                downloadLink.style.display = 'block'; // Use style.display
                uploadResultsArea.classList.remove('hidden');
            } else {
                uploadStatus.textContent = `Error: ${result.error || 'Upload failed'}`;
            }
        } catch (error) {
            console.error('Upload error:', error);
            uploadStatus.textContent = `Error: ${error.message}`;
        } finally {
             // Clear the file input after upload attempt
             videoFile.value = '';
        }
    });


    // --- Webcam Logic ---

    function startFrameProcessing() {
        // This function ONLY starts the interval, assuming videoStream is ready
        if (!videoStream || processingInterval) {
             console.warn("startFrameProcessing called without ready stream or already processing.");
             return; // Don't start if stream isn't ready or already processing
        }

        status.textContent = 'Capturing frames...';
        collectedLandmarks = []; // Reset data
        frameCount.textContent = '0';
        resultsArea.classList.add('hidden');
        webcamDownloadLink.style.display = 'none';

        processingInterval = setInterval(() => {
            // Ensure the video dimensions are available and canvas is sized
            if (webcamFeed.readyState >= webcamFeed.HAVE_CURRENT_DATA && webcamFeed.videoWidth > 0) {
                 // Match canvas size to video frame size if not already set
                if (canvas.width !== webcamFeed.videoWidth || canvas.height !== webcamFeed.videoHeight) {
                    canvas.width = webcamFeed.videoWidth;
                    canvas.height = webcamFeed.videoHeight;
                    console.log(`Canvas resized to: ${canvas.width}x${canvas.height}`);
                }

                // Draw video frame to canvas
                ctx.drawImage(webcamFeed, 0, 0, canvas.width, canvas.height);
                // Get base64 data URL
                const frameData = canvas.toDataURL('image/jpeg', 0.8);
                // Send frame to server via Socket.IO
                socket.emit('process_frame', frameData);
            } else {
                // console.log("Webcam not ready yet or dimensions 0...");
            }
        }, 1000 / frameRate);
    }

    async function handleStartClick() {
        startButton.disabled = true; // Disable start button immediately
        status.textContent = 'Starting webcam...';

        try {
            if (!videoStream) { // Only get stream if it doesn't exist
                videoStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                webcamFeed.srcObject = videoStream;
                // Use a promise to wait for metadata to load
                await new Promise((resolve) => {
                    webcamFeed.onloadedmetadata = () => {
                        console.log("Metadata loaded");
                        resolve();
                    };
                });
            }

             // Ensure canvas is set up before starting interval (might be redundant if done in interval, but safe)
             canvas.width = webcamFeed.videoWidth;
             canvas.height = webcamFeed.videoHeight;
             console.log(`Webcam started: ${canvas.width}x${canvas.height}`);

            // Now start the frame processing interval
            startFrameProcessing();

            stopButton.disabled = false; // Enable stop button ONLY after successful start

        } catch (err) {
            console.error("Error accessing or starting webcam:", err);
            status.textContent = `Error: ${err.message}`;
            // If error occurred, ensure stream is stopped and state is reset
            if (videoStream) {
                videoStream.getTracks().forEach(track => track.stop());
                videoStream = null;
                webcamFeed.srcObject = null;
            }
            startButton.disabled = false; // Re-enable start button on error
            stopButton.disabled = true;
        }
    }

    function handleStopClick() {
        stopButton.disabled = true; // Disable stop button immediately
        startButton.disabled = false; // Enable start button

        if (processingInterval) {
            clearInterval(processingInterval);
            processingInterval = null;
            console.log("Processing interval stopped.");
        }

        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            videoStream = null;
            webcamFeed.srcObject = null; // Turn off video element display
            console.log("Webcam stream stopped.");
        }

        status.textContent = `Capture stopped. ${collectedLandmarks.length} frames collected.`;

        if (collectedLandmarks.length > 0) {
            resultsArea.classList.remove('hidden');
            const jsonData = JSON.stringify(collectedLandmarks, null, 2); // Pretty print
            const blob = new Blob([jsonData], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            webcamDownloadLink.href = url;
            const timestamp = new Date().toISOString().replace(/[:\-T\.Z]/g, ''); // Cleaner timestamp
            webcamDownloadLink.download = `webcam_landmarks_${timestamp}.json`;
            webcamDownloadLink.style.display = 'block';
        } else {
            resultsArea.classList.add('hidden');
            webcamDownloadLink.style.display = 'none';
            console.log("No landmarks collected.")
        }
    }

    // --- SocketIO Event Listeners ---
    socket.on('connect', () => {
        console.log('Connected to server via Socket.IO');
        status.textContent = 'Ready. Press Start Capture.';
        // **Remove automatic webcam start here**
        // startWebcam(); // DON'T start webcam automatically
        // Set initial button state correctly
        startButton.disabled = false;
        stopButton.disabled = true;
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        status.textContent = 'Disconnected. Please refresh.';
        handleStopClick(); // Stop everything if disconnected
    });

    socket.on('frame_result', (data) => {
        if (processingInterval) { // Only collect if we are actively capturing
            if (data.error) {
                 console.error("Backend Error:", data.error);
                 // Optionally display this error to the user more prominently
                 // status.textContent = `Backend Error: ${data.error}`; // Might be too spammy
            } else if (data.landmarks) {
                collectedLandmarks.push(data.landmarks);
                frameCount.textContent = collectedLandmarks.length.toString();
            }
        }
    });

    // --- Event Listeners ---
    startButton.addEventListener('click', handleStartClick);
    stopButton.addEventListener('click', handleStopClick);

    // --- Initial UI State ---
    status.textContent = 'Initializing...'; // Change to Ready on connect
    startButton.disabled = true; // Disable until socket connects
    stopButton.disabled = true;
    resultsArea.classList.add('hidden');
    uploadResultsArea.classList.add('hidden');
    downloadLink.style.display = 'none';
    webcamDownloadLink.style.display = 'none';

}); // End DOMContentLoaded