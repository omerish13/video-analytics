import json
import time

import cv2
from entities import (
    TEMP_DIR, setup_nats_connection, setup_jetstream,
)

from utils.logger import logger
import asyncio
import os


class VideoStreamer:
    def __init__(self, video_path, stream_name):
        self.video_path = video_path
        self.stream_name = stream_name
        self.frame_id = 0
        self.total_frames = 0
        self.original_fps = 0

    async def start_streaming(self):
        """Stream video frames to NATS JetStream"""
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

        # Connect to NATS
        nc = await setup_nats_connection()
        js = await setup_jetstream(nc)

        try:
            start_time = time.time()
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Save the frame to disk instead of sending it directly
                frame_filename = f"{self.frame_id:06d}.jpg"
                frame_path = os.path.join(TEMP_DIR, frame_filename)

                # Optimize image quality/size ratio
                cv2.imwrite(frame_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

                # Send only the metadata and file path via NATS
                frame_data = {
                    'frame_id': self.frame_id,
                    'timestamp': time.time(),
                    'original_fps': self.original_fps,
                    'width': original_width,
                    'height': original_height,
                    'frame_path': frame_path,  # Store path to file instead of actual frame data
                    'is_last_frame': False
                }

                # Convert to JSON string
                message = json.dumps(frame_data)

                # Publish message to NATS JetStream
                subject = f"{self.stream_name}.frame"
                await js.publish(subject, message.encode())

                self.frame_id += 1

                # Report progress
                if self.frame_id % 100 == 0:
                    elapsed = time.time() - start_time
                    frames_per_second = self.frame_id / elapsed if elapsed > 0 else 0
                    logger.info(f"Streamed {self.frame_id}/{self.total_frames} frames ({self.frame_id/self.total_frames*100:.1f}%) at {frames_per_second:.1f} FPS")

            # Send a final message indicating end of stream
            end_message = {
                'frame_id': self.frame_id,
                'timestamp': time.time(),
                'original_fps': self.original_fps,
                'width': original_width,
                'height': original_height,
                'frame_path': '',  # Empty frame path
                'is_last_frame': True
            }

            await js.publish(f"{self.stream_name}.frame", json.dumps(end_message).encode())
            logger.info(f"Streamed all {self.frame_id} frames. Sending end-of-stream signal.")

        finally:
            cap.release()
            await nc.close()
            logger.info("Video Streamer finished")

    def start(self):
        """Start the video streamer (non-async wrapper)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start_streaming())
