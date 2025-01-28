from typing import Generator
import cv2

class Streamer:
    def __init__(self, video_path):
        self.video_path = video_path

    def frame_generator(self)->Generator[tuple, None, None]:
        """
        Generates video frames and timestamps.

        Raises:
            ValueError: If the video file cannot be opened.

        Yields:
            tuple: A tuple containing:
                - numpy.ndarray: A video frame.
                - int: The timestamp of the video frame.
        """
        video_capture = cv2.VideoCapture(self.video_path)
        if not video_capture.isOpened():
            raise ValueError(f"Error: Could not open video file {self.video_path}")
        
        while True:
            ret, frame = video_capture.read()
            if not ret:
                break
            timestamp = video_capture.get(cv2.CAP_PROP_POS_MSEC)
            # yield the frame and timestamp
            yield frame, timestamp

        video_capture.release()
