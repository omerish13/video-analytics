import json

import cv2

from utils.logger import logger
import asyncio
from entities import (
    DETECTION_THRESHOLD, setup_nats_connection, setup_jetstream,
)
from nats.js.api import ConsumerConfig

class MotionDetector:
    def __init__(self, input_stream, output_stream):
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.prev_frame = None
        self.processed_frames = 0

    async def process_frame(self, msg):
        """Process a frame from NATS JetStream"""
        try:
            # Parse the message data
            frame_data = json.loads(msg.data.decode())
            frame_id = frame_data['frame_id']

            # Check if this is the last frame signal
            if frame_data.get('is_last_frame', False):
                # Forward the end-of-stream signal
                await self.js.publish(
                    f"{self.output_stream}.detection",
                    json.dumps(frame_data).encode()
                )
                logger.info("Motion Detector received end-of-stream signal. Forwarding to Display.")
                return

            # Read frame from file instead of from message
            frame_path = frame_data['frame_path']
            frame = cv2.imread(frame_path)

            if frame is None:
                logger.warning(f"Could not read frame from {frame_path}")
                return

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
                    'frame_path': frame_path,  # Pass through the frame path
                    'motion_regions': [],
                    'is_last_frame': False
                }

                await self.js.publish(
                    f"{self.output_stream}.detection",
                    json.dumps(output_data).encode()
                )

                self.processed_frames += 1
                return

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

            # Create output data with frame path and detected regions
            output_data = {
                'frame_id': frame_id,
                'timestamp': frame_data['timestamp'],
                'original_fps': frame_data.get('original_fps', 30.0),
                'width': frame_data.get('width', 0),
                'height': frame_data.get('height', 0),
                'frame_path': frame_path,  # Pass through the frame path
                'motion_regions': motion_regions,
                'is_last_frame': False
            }

            # Send to output stream
            await self.js.publish(
                f"{self.output_stream}.detection",
                json.dumps(output_data).encode()
            )

            self.processed_frames += 1

            # Report progress occasionally
            if self.processed_frames % 100 == 0:
                logger.info(f"Detector processed {self.processed_frames} frames")

        except Exception as e:
            logger.error(f"Error processing frame: {e}")

    async def start_detection(self):
        """Start consuming frames and detecting motion"""
        logger.info("Starting Motion Detector...")

        # Connect to NATS
        self.nc = await setup_nats_connection()
        self.js = await setup_jetstream(self.nc)

        try:
            # Set up consumer with flow control
            consumer_config = ConsumerConfig(
                durable_name="motion_detector",
                deliver_subject="motion_detector.deliver",
                ack_policy="explicit",
                max_deliver=1,
                flow_control=True
            )

            # Create the consumer
            await self.js.subscribe(
                f"{self.input_stream}.frame",
                stream=self.input_stream,
                cb=self.process_frame,
                config=consumer_config
            )

            # Wait for end-of-stream signal or timeout
            detection_active = True
            last_count = 0
            inactive_count = 0

            while detection_active:
                await asyncio.sleep(5)

                if self.processed_frames == last_count:
                    inactive_count += 1
                    if inactive_count > 6:  # 30 seconds of inactivity
                        logger.info("No frames processed for 30 seconds, assuming stream has ended")
                        detection_active = False
                else:
                    inactive_count = 0
                    last_count = self.processed_frames
                    logger.info(f"Motion Detector active, processed {self.processed_frames} frames")

        except Exception as e:
            logger.error(f"Error in Motion Detector: {e}")
        finally:
            await self.nc.close()
            logger.info(f"Motion Detector finished. Processed {self.processed_frames} frames.")

    def start(self):
        """Start the motion detector (non-async wrapper)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start_detection())
