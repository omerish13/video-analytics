import cv2
import numpy

class Display:
    def __init__(self):
        pass

    def draw_movement(self, frame: numpy.ndarray, x: int, y: int, w: int, h: int) -> None:
        """
        Draw a rectangle around the detected movement region.

        Args:
            frame (numpy.ndarray): The video frame to draw on.
            x (int): The x-coordinate of the top-left corner of the rectangle.
            y (int): The y-coordinate of the top-left corner of the rectangle.
            w (int): The width of the rectangle.
            h (int): The height of the rectangle.
        """
        # Blur the detected movement region
        movement_region = frame[y:y+h, x:x+w]
        blurred_region = cv2.GaussianBlur(movement_region, (15, 15), 0)
        frame[y:y+h, x:x+w] = blurred_region

        # Draw a rectangle around the detected movement
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    def add_timestamp(self, frame: numpy.ndarray, timestamp: int) -> None:
        """
        Add a timestamp overlay to the video frame.

        Args:
            frame (numpy.ndarray): The video frame to add the timestamp to.
            timestamp (int): The timestamp in milliseconds.
        """
        # Add timestamp to the top-left corner
        time_in_seconds = int(timestamp / 1000)
        cv2.putText(frame, f"Time: {time_in_seconds}s", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    def draw_frame(self, frame: numpy.ndarray, movements: list, timestamp: int) -> numpy.ndarray:
        """
        Draw the video frame with detected movements and timestamp.

        Args:
            frame (numpy.ndarray): The video frame to be displayed.
            movements (list): List of tuples (x, y, w, h) representing detected movement regions.
            timestamp (int): The timestamp in milliseconds.
        Returns:
            numpy.ndarray: The modified video frame with movements and timestamp.
        """
        for (x, y, w, h) in movements:
            self.draw_movement(frame, x, y, w, h)
        
        self.add_timestamp(frame, timestamp)

        return frame

    def show_frame(self, frame: numpy.ndarray) -> bool:
        """
        Display a frame with detected movements and timestamp.

        This function takes a video frame, draws rectangles around detected movements,
        adds a timestamp overlay, and displays the resulting frame. The function also
        handles user input for quitting the display.
            
        Args:
            frame (numpy.ndarray): The video frame to be displayed

        Returns:
            bool: True if user pressed 'q' to quit, False otherwise
        """

        # Display the frame
        cv2.imshow("Detected Movements", frame)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return True  # Indicate user wants to quit
        return False
