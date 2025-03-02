
import time
import threading
from entities.streamer import VideoStreamer
from entities.detector import MotionDetector
from entities.display import VideoDisplay
from entities import KAFKA_BOOTSTRAP_SERVERS, FRAME_TOPIC, DETECTION_TOPIC, OUTPUT_VIDEO_PATH
from entities import processing_complete, setup_kafka_topics, delete_kafka_topics
from utils.menu import get_video_path
from entities import logger



def main():
    # Create new Kafka topics for this run
    setup_kafka_topics()

    video_path = get_video_path()
    if not video_path:
        logger.error("Error: Video path is empty. Exiting.")
        return
    
    try:
        # Create instances of the three components
        streamer = VideoStreamer(video_path, KAFKA_BOOTSTRAP_SERVERS, FRAME_TOPIC)
        detector = MotionDetector(KAFKA_BOOTSTRAP_SERVERS, FRAME_TOPIC, DETECTION_TOPIC)
        display = VideoDisplay(KAFKA_BOOTSTRAP_SERVERS, DETECTION_TOPIC, OUTPUT_VIDEO_PATH)
        
        logger.info("Motion detection system starting...")
        logger.info(f"Processing video: {video_path}")
        logger.info(f"Topics: frames={FRAME_TOPIC}, detections={DETECTION_TOPIC}")
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
        # Delete Kafka topics used for this run
        delete_kafka_topics()
        logger.info("Application exited")

if __name__ == "__main__":
    main()
