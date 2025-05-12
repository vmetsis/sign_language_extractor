# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install system dependencies needed by OpenCV, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    # Add other libraries here if more errors pop up
    # Clean up apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    # Now install Python packages
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Make port 5000 available to the world outside this container
# (Flask default port, also used by eventlet/gevent)
EXPOSE 5000

# Define environment variables (optional, good practice)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1 

# Create directories needed by the app if they don't exist
RUN mkdir -p uploads data

# Command to run the application using eventlet for SocketIO
CMD ["python", "app.py"]
