import cv2
import numpy

class Detector:
    def __init__(self):
        pass

    def detect_movements(self, frame: numpy.ndarray, prev_frame: numpy.ndarray) -> tuple:
        """
        Detects movements between the current frame and the previous frame.

        Args:
            frame (numpy.ndarray): The current video frame.
            prev_frame (numpy.ndarray): The previous video frame.

        Returns:
            tuple: A tuple containing:
                - list: A list of bounding rectangles for detected movements.
                - numpy.ndarray: The processed grayscale version of the current frame.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_frame is None:
            return [], gray  # No movements detected on the previous frame

        # Compute the absolute difference between the current and previous frames
        delta_frame = cv2.absdiff(prev_frame, gray)
        thresh = cv2.threshold(delta_frame, 30, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        movements = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > 500]
        return movements, gray