import cv2
import json
import numpy as np
from kafka import KafkaConsumer, KafkaProducer
import uuid
from entities import DETECTION_THRESHOLD,logger, MAX_MESSAGE_SIZE

class MotionDetector:
    def __init__(self, kafka_bootstrap_servers, input_topic, output_topic):
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.consumer = KafkaConsumer(
            self.input_topic,
            bootstrap_servers=kafka_bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id=f'motion-detector-{uuid.uuid4()}',
            consumer_timeout_ms=10000,  # 10 second timeout if no messages
            fetch_max_bytes=MAX_MESSAGE_SIZE,
            max_partition_fetch_bytes=MAX_MESSAGE_SIZE
        )
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            max_request_size=MAX_MESSAGE_SIZE,
            buffer_memory=MAX_MESSAGE_SIZE * 10
        )
        self.prev_frame = None
        self.processed_frames = 0
        
    def start(self):
        logger.info("Starting Motion Detector...")
        try:
            for message in self.consumer:
                frame_data = message.value
                frame_id = frame_data['frame_id']
                
                # Check if this is the last frame signal
                if frame_data.get('is_last_frame', False):
                    # Forward the end-of-stream signal
                    self.producer.send(self.output_topic, frame_data)
                    logger.info("Motion Detector received end-of-stream signal. Forwarding to Display.")
                    break
                
                # Convert hex string back to bytes and decode image
                frame_bytes = bytes.fromhex(frame_data['frame'])
                frame_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
                
                # Convert to grayscale for motion detection
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)
                
                # Initialize previous frame for the first frame
                if self.prev_frame is None:
                    self.prev_frame = gray
                    # Forward first frame with no motion
                    output_data = {
                        'frame_id': frame_id,
                        'timestamp': frame_data['timestamp'],
                        'original_fps': frame_data.get('original_fps', 30.0),
                        'width': frame_data.get('width', 0),
                        'height': frame_data.get('height', 0),
                        'frame': frame_data['frame'],
                        'motion_regions': [],
                        'is_last_frame': False
                    }
                    self.producer.send(self.output_topic, output_data)
                    self.processed_frames += 1
                    continue
                
                # Calculate absolute difference between current and previous frame
                frame_delta = cv2.absdiff(self.prev_frame, gray)
                thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                
                # Dilate the thresholded image to fill in holes
                thresh = cv2.dilate(thresh, None, iterations=2)
                
                # Find contours on thresholded image
                contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                motion_regions = []
                for contour in contours:
                    if cv2.contourArea(contour) < DETECTION_THRESHOLD:
                        continue
                    
                    (x, y, w, h) = cv2.boundingRect(contour)
                    motion_regions.append({
                        'x': int(x),
                        'y': int(y),
                        'w': int(w),
                        'h': int(h)
                    })
                
                # Update previous frame
                self.prev_frame = gray
                
                # Create output data with original frame and detected regions
                output_data = {
                    'frame_id': frame_id,
                    'timestamp': frame_data['timestamp'],
                    'original_fps': frame_data.get('original_fps', 30.0),
                    'width': frame_data.get('width', 0),
                    'height': frame_data.get('height', 0),
                    'frame': frame_data['frame'],
                    'motion_regions': motion_regions,
                    'is_last_frame': False
                }
                
                # Send to output topic
                self.producer.send(self.output_topic, output_data)
                self.processed_frames += 1
                
                # Report progress occasionally
                if self.processed_frames % 100 == 0:
                    logger.info(f"Detector processed {self.processed_frames} frames")
                
        except Exception as e:
            logger.error(f"Error in Motion Detector: {e}")
        finally:
            self.producer.flush()
            logger.info(f"Motion Detector finished. Processed {self.processed_frames} frames.")
