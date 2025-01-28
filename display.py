import cv2
import numpy

class Display:
    def __init__(self):
        pass

    def show_frame(self, frame: numpy.ndarray, movements: list, timestamp: int) -> bool:
        """
        Display a frame with detected movements and timestamp.

        This function takes a video frame, draws rectangles around detected movements,
        adds a timestamp overlay, and displays the resulting frame. The function also
        handles user input for quitting the display.
            
        Args:
            frame (numpy.ndarray): The video frame to be displayed
            movements (list): List of tuples (x, y, w, h) representing detected movement regions
            timestamp (int): Timestamp in milliseconds

        Returns:
            bool: True if user pressed 'q' to quit, False otherwise
        """
        for (x, y, w, h) in movements:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Add timestamp to the top-left corner
        time_in_seconds = int(timestamp / 1000)
        cv2.putText(frame, f"Time: {time_in_seconds}s", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Display the frame
        cv2.imshow("Detected Movements", frame)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return True  # Indicate user wants to quit
        return False
