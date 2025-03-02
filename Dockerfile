# Use official Python image
FROM python:3.9

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0

# Copy all files into the container
COPY . /app

# Install required Python libraries
RUN pip install --no-cache-dir confluent-kafka opencv-python numpy flask

# Default command (overridden in docker-compose)
CMD ["python3", "main.py"]
