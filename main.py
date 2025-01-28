from streamer import Streamer
from detector import Detector
from display import Display
from menu import get_video_path
import cv2
import time

def preprocess_video(video_path):
    """
    Preprocess the video to detect movements and store results.
    
    Returns:
        results (list): A list of tuples (frame, movements, timestamp).
    """
    streamer = Streamer(video_path)
    detector = Detector()

    results = []
    prev_frame = None

    for frame, timestamp in streamer.frame_generator():
        # Detect movements
        movements, prev_frame = detector.detect_movements(frame, prev_frame)
        # Store results
        results.append((frame, movements, timestamp))

    return results

def playback_results(results):
    """
    Playback the stored results according to the original video timing.
    """
    display = Display()
    start_time = time.time()

    for frame, movements, timestamp in results:
        # Synchronize to the original video timing
        elapsed_time = (time.time() - start_time) * 1000  # Elapsed time in milliseconds
        while elapsed_time < timestamp:
            time.sleep(0.001)  # Wait until it's time to display the frame
            elapsed_time = (time.time() - start_time) * 1000
        

        # Display the frame
        if display.show_frame(display.draw_frame(frame, movements, timestamp)):
            break  # Exit on user request

    print("Video playback complete.")
    cv2.destroyAllWindows()

if __name__ == "__main__":
    video_path = get_video_path()

    # Preprocess the video
    print("Preprocessing video...")
    results = preprocess_video(video_path)

    # Playback the results
    print("Playing back results...")
    playback_results(results)

    