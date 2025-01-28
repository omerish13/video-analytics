from streamer import Streamer
from detector import Detector
from display import Display
import time
import cv2

def main(video_path):
    # Instantiate components
    streamer = Streamer(video_path)
    detector = Detector()
    display = Display()

    prev_frame = None
    last_frame_time = time.time()

    # Process video frames
    for frame, timestamp, frame_delay in streamer.frame_generator():
        # Adjust for real-time playback using precise timing
        current_time = time.time()
        elapsed_time = current_time - last_frame_time
        if elapsed_time < frame_delay:
            time.sleep(frame_delay - elapsed_time)
        last_frame_time = time.time()

        # Detect movements
        movements, prev_frame = detector.detect_movements(frame, prev_frame)

        # Display the frame
        if display.show_frame(frame, movements, timestamp):
            break  # Exit on user request

    print("Video processing complete.")
    cv2.destroyAllWindows()

if __name__ == "__main__":
    video_path = "./files/sample.mp4"  # Replace with your video file path
    main(video_path)