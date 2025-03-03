import threading
import time

from entities.streamer import VideoStreamer
from entities.detector import MotionDetector
from entities.display import VideoDisplay
from entities import (
    setup_nats_streams_sync, delete_nats_streams_sync, clean_temp_files,
    VIDEO_PATH, FRAME_STREAM, DETECTION_STREAM, TEMP_DIR, OUTPUT_VIDEO_PATH,
    processing_complete
)
from utils.logger import logger

def main():
    # Create NATS streams for this run
    setup_nats_streams_sync()

    try:
        # Create instances of the three components
        streamer = VideoStreamer(VIDEO_PATH, FRAME_STREAM)
        detector = MotionDetector(FRAME_STREAM, DETECTION_STREAM)
        display = VideoDisplay(DETECTION_STREAM, OUTPUT_VIDEO_PATH)

        logger.info("Motion detection system starting...")
        logger.info(f"Processing video: {VIDEO_PATH}")
        logger.info(f"Streams: frames={FRAME_STREAM}, detections={DETECTION_STREAM}")
        logger.info(f"Using temporary directory for frames: {TEMP_DIR}")
        logger.info("Results will be saved to a video file for playback after processing")

        # Start each component in a separate thread
        streamer_thread = threading.Thread(target=streamer.start)
        detector_thread = threading.Thread(target=detector.start)
        display_thread = threading.Thread(target=display.start)

        # Mark threads as daemon so they exit when main thread exits
        streamer_thread.daemon = True
        detector_thread.daemon = True
        display_thread.daemon = True

        # Start the threads
        streamer_thread.start()
        detector_thread.start()
        display_thread.start()

        # Wait for all threads to complete with a timeout mechanism
        max_wait_time = 3600  # 1 hour max
        wait_time = 0
        check_interval = 5  # Check every 5 seconds

        while (streamer_thread.is_alive() or detector_thread.is_alive() or display_thread.is_alive()) and wait_time < max_wait_time:
            time.sleep(check_interval)
            wait_time += check_interval

            if processing_complete:
                logger.info("Processing complete. Breaking out of wait loop.")
                break

        if wait_time >= max_wait_time:
            logger.warning("WARNING: Processing timed out after 1 hour.")

        # Play the processed video once processing is complete
        logger.info("Processing complete. Playing the result video...")
        display.play_video()

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Delete NATS streams used for this run
        delete_nats_streams_sync()
        # Clean up temporary files
        clean_temp_files()
        logger.info("Application exited")

if __name__ == "__main__":
    main()
