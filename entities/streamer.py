import cv2
import time
from kafka import KafkaProducer
import json
from entities import MAX_MESSAGE_SIZE, logger

class VideoStreamer:
    def __init__(self, video_path, kafka_bootstrap_servers, topic):
        self.video_path = video_path
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            max_request_size=MAX_MESSAGE_SIZE,
            buffer_memory=MAX_MESSAGE_SIZE * 10  # Allow buffering multiple messages
        )
        self.frame_id = 0
        self.total_frames = 0
        self.original_fps = 0

    def start(self):
        logger.info("Starting Video Streamer...")
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"Error: Could not open video file {self.video_path}")
            return

        # Get total frame count and FPS for progress reporting
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.original_fps = cap.get(cv2.CAP_PROP_FPS)
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"Video info: {self.total_frames} frames at {self.original_fps} FPS, resolution: {original_width}x{original_height}")
        
        try:
            start_time = time.time()
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Optimize image quality/size ratio for Kafka
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                frame_data = {
                    'frame_id': self.frame_id,
                    'timestamp': time.time(),
                    'original_fps': self.original_fps,
                    'width': original_width,
                    'height': original_height,
                    'frame': buffer.tobytes().hex(),  # Convert bytes to hex string
                    'is_last_frame': False  # Flag to indicate if this is the last frame
                }
                
                self.frame_id += 1
                
                # Report progress
                if self.frame_id % 100 == 0:
                    elapsed = time.time() - start_time
                    frames_per_second = self.frame_id / elapsed if elapsed > 0 else 0
                    logger.info(f"Streamed {self.frame_id}/{self.total_frames} frames ({self.frame_id/self.total_frames*100:.1f}%) at {frames_per_second:.1f} FPS")
                
                # Send frame to Kafka
                self.producer.send(self.topic, frame_data)
                
                # No delay - process as fast as possible
                
            # Send a final message indicating end of stream
            end_message = {
                'frame_id': self.frame_id,
                'timestamp': time.time(),
                'original_fps': self.original_fps,
                'width': original_width,
                'height': original_height,
                'frame': '',  # Empty frame
                'is_last_frame': True
            }
            self.producer.send(self.topic, end_message)
            logger.info(f"Streamed all {self.frame_id} frames. Sending end-of-stream signal.")
                
        finally:
            cap.release()
            self.producer.flush()
            logger.info("Video Streamer finished")
