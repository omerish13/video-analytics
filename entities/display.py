import cv2
import json
import numpy as np
from kafka import KafkaConsumer
import os
import uuid
from entities import BLUR_AMOUNT, OUTPUT_VIDEO_PATH, MAX_MESSAGE_SIZE, logger
import time

class VideoDisplay:
    def __init__(self, kafka_bootstrap_servers, topic, output_video_path=OUTPUT_VIDEO_PATH):
        """
        Initialize the VideoDisplay component that creates a temporary video file.
        
        Args:
            kafka_bootstrap_servers (str): Kafka broker address
            topic (str): Kafka topic to consume from
            output_video_path (str): Path to save the output video
        """
        # Initialize Kafka consumer
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=kafka_bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id=f'video-display-{uuid.uuid4()}',
            consumer_timeout_ms=15000,  # 15 second timeout if no messages
            fetch_max_bytes=MAX_MESSAGE_SIZE,
            max_partition_fetch_bytes=MAX_MESSAGE_SIZE
        )
        
        self.output_video_path = output_video_path
        self.video_writer = None
        self.frame_buffer = []  # Store frames if we need to determine video properties first
        self.frame_count = 0
        self.original_fps = 30.0  # Default, will be updated from messages
        self.last_frame_id = -1  # Track the last frame ID to ensure we process in order
        self.expected_frames = 0  # Total expected frames
        self.width = 0
        self.height = 0
    
    def process_frame(self, frame, movements):
        """
        Process a frame by drawing rectangles and applying blur to motion regions.
        
        Args:
            frame (numpy.ndarray): The video frame to process
            movements (list): List of dictionaries with motion region coordinates
            
        Returns:
            numpy.ndarray: The processed frame
        """
        # Draw rectangles and apply blur for motion regions
        for region in movements:
            x, y, w, h = region['x'], region['y'], region['w'], region['h']
            
            # Make sure region is within the frame boundaries
            if x < 0 or y < 0 or x + w > frame.shape[1] or y + h > frame.shape[0]:
                # Adjust coordinates to stay within the frame
                x = max(0, x)
                y = max(0, y)
                w = min(w, frame.shape[1] - x)
                h = min(h, frame.shape[0] - y)
                
                # Skip if region is now invalid
                if w <= 0 or h <= 0:
                    continue
            
            # Create a copy of the region to blur
            roi = frame[y:y+h, x:x+w].copy()
            
            # Apply blur to the region
            blurred_roi = cv2.GaussianBlur(roi, (BLUR_AMOUNT, BLUR_AMOUNT), 0)
            
            # Put the blurred region back to the frame
            frame[y:y+h, x:x+w] = blurred_roi
            
            # Draw a rectangle around the region
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
        # Add frame information as text
        cv2.putText(frame, f"Frame: {self.frame_count}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, f"Motion Regions: {len(movements)}", (10, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return frame
    
    def initialize_video_writer(self, width, height):
        """
        Initialize the video writer with the frame properties.
        
        Args:
            width (int): Frame width
            height (int): Frame height
        """
        # Use a codec that works well with quality and speed
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use mp4v codec
        self.video_writer = cv2.VideoWriter(
            self.output_video_path, 
            fourcc, 
            self.original_fps,  # Use original video FPS
            (width, height)
        )
        
        # Write any buffered frames
        for buffered_frame in self.frame_buffer:
            self.video_writer.write(buffered_frame)
        self.frame_buffer = []  # Clear the buffer
    
    def start(self):
        """Process frames from Kafka and save to a temporary video file."""
        logger.info("Starting Video Display (saving to video file)...")
        global processing_complete
        start_time = time.time()
        
        try:
            # First pass: collect all frame data in order to properly process all frames
            all_frames = []
            metadata_received = False
            
            for message in self.consumer:
                data = message.value
                
                # Update metadata if provided
                if 'original_fps' in data:
                    self.original_fps = data['original_fps']
                if 'width' in data and 'height' in data:
                    self.width = data['width']
                    self.height = data['height']
                    metadata_received = True
                    
                # Check if this is the end-of-stream signal
                if data.get('is_last_frame', False):
                    self.expected_frames = data.get('frame_id', 0)
                    logger.info(f"VideoDisplay received end-of-stream signal. Expecting {self.expected_frames} frames.")
                    break
                
                # Store the frame data for processing
                if not data.get('is_last_frame', False):
                    all_frames.append(data)
            
            # Sort frames by frame_id
            all_frames.sort(key=lambda x: x['frame_id'])
            
            # Process all frames in order
            for data in all_frames:
                frame_id = data['frame_id']
                
                # Convert hex string back to bytes and decode image
                try:
                    frame_bytes = bytes.fromhex(data['frame'])
                    frame_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
                    
                    if frame is None:
                        logger.warning(f"Warning: Failed to decode frame {frame_id}")
                        continue
                except Exception as e:
                    logger.error(f"Error decoding frame {frame_id}: {e}")
                    continue
                
                # Process the frame
                processed_frame = self.process_frame(frame, data['motion_regions'])
                self.frame_count += 1
                
                # Initialize video writer if not already done
                if self.video_writer is None and frame is not None:
                    if metadata_received:
                        self.initialize_video_writer(self.width, self.height)
                    else:
                        self.initialize_video_writer(frame.shape[1], frame.shape[0])
                
                # Write frame to the video file
                if self.video_writer is not None:
                    self.video_writer.write(processed_frame)
                else:
                    # Buffer the frame until we can initialize the writer
                    self.frame_buffer.append(processed_frame)
                
                # Report progress occasionally
                if self.frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    frames_per_second = self.frame_count / elapsed if elapsed > 0 else 0
                    completion = (self.frame_count / self.expected_frames * 100) if self.expected_frames > 0 else 0
                    logger.info(f"Display processed {self.frame_count} frames ({completion:.1f}%) at {frames_per_second:.1f} FPS")
                    
        except Exception as e:
            logger.error(f"Error in Video Display: {e}")
        finally:
            # Release the video writer
            if self.video_writer is not None:
                self.video_writer.release()
            
            elapsed = time.time() - start_time
            frames_per_second = self.frame_count / elapsed if elapsed > 0 else 0
            logger.info(f"Video Display finished. Processed {self.frame_count} frames at {frames_per_second:.1f} FPS")
            processing_complete = True
            
    def play_video(self):
        """Play the created video and then delete it."""
        if not os.path.exists(self.output_video_path):
            logger.warning(f"No video file found at {self.output_video_path}")
            return
            
        logger.info(f"Playing the processed video: {self.output_video_path}")
        
        try:
            # Open the video file
            cap = cv2.VideoCapture(self.output_video_path)
            if not cap.isOpened():
                logger.error(f"Error: Could not open video file {self.output_video_path}")
                return
                
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_delay = int(1000 / fps)  # Delay in milliseconds
            
            logger.info(f"Video playback: {total_frames} frames at {fps} FPS")
            
            # Create a window for display
            cv2.namedWindow('Processed Video', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('Processed Video', 1280, 720)
                
            # Play the video
            frame_idx = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_idx += 1
                
                # Add progress indicator
                progress = frame_idx / total_frames * 100
                cv2.putText(frame, f"Playback: {frame_idx}/{total_frames} ({progress:.1f}%)", 
                           (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (255, 255, 255), 2)
                
                # Display the frame
                cv2.imshow('Processed Video', frame)
                
                # Exit if 'q' is pressed
                key = cv2.waitKey(frame_delay) & 0xFF
                if key == ord('q'):
                    logger.info("User pressed 'q'. Stopping playback.")
                    break
                
                # Report progress occasionally
                if frame_idx % 100 == 0:
                    logger.info(f"Playback: {frame_idx}/{total_frames} frames ({progress:.1f}%)")
                    
        except Exception as e:
            logger.error(f"Error playing video: {e}")
        finally:
            # Release resources
            cap.release()
            cv2.destroyAllWindows()
            
            # Delete the temporary video file
            try:
                os.remove(self.output_video_path)
                logger.info(f"Deleted temporary video file: {self.output_video_path}")
            except Exception as e:
                logger.error(f"Error deleting temporary file: {e}")
