import cv2

class Streamer:
    def __init__(self, video_path):
        self.video_path = video_path

    def frame_generator(self):
        """
        Generator that reads frames from the video file and yields them one by one.
        """
        video_capture = cv2.VideoCapture(self.video_path)
        if not video_capture.isOpened():
            raise ValueError(f"Error: Could not open video file {self.video_path}")
        
        while True:
            ret, frame = video_capture.read()
            if not ret:  # End of video
                break
            timestamp = video_capture.get(cv2.CAP_PROP_POS_MSEC)
            yield frame, timestamp  # Yield frame and timestamp

        video_capture.release()
