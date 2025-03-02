import hashlib
import logging
import os
import time

from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import UnknownTopicOrPartitionError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('motion_detection')

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
VIDEO_PATH = 'files/sample.mp4'  # Path to your video file
DETECTION_THRESHOLD = 5000  # Adjust sensitivity of motion detection
BLUR_AMOUNT = 15  # Higher values mean more blur
OUTPUT_VIDEO_PATH = 'processed_video.mp4'  # Temporary output file
MAX_MESSAGE_SIZE = 20971520  # 20MB for larger frames

# Generate unique topic names based on the video file
def generate_topic_names(video_path):
    """Generate unique topic names based on the video file path"""
    # Create a unique hash based on the video path and current timestamp
    hash_input = f"{video_path}_{time.time()}"
    hash_obj = hashlib.md5(hash_input.encode())
    hash_str = hash_obj.hexdigest()[:8]  # Use first 8 chars of hash

    # Get video filename without extension
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # Create safe topic names (Kafka topics have naming restrictions)
    safe_name = ''.join(c if c.isalnum() else '_' for c in video_name)

    # Create unique topic names
    frame_topic = f"frames_{safe_name}_{hash_str}"
    detection_topic = f"detections_{safe_name}_{hash_str}"

    return frame_topic, detection_topic

# Generate the topic names for this run
FRAME_TOPIC, DETECTION_TOPIC = generate_topic_names(VIDEO_PATH)

# Global flag for signaling completion
processing_complete = False

def setup_kafka_topics():
    """Create new Kafka topics for this video processing run"""
    admin_client = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

    # Create new topics for this run
    topics_to_create = [
        NewTopic(FRAME_TOPIC, 1, 1),
        NewTopic(DETECTION_TOPIC, 1, 1)
    ]

    try:
        admin_client.create_topics(topics_to_create)
        logger.info(f"Created Kafka topics: {[t.name for t in topics_to_create]}")
    except Exception as e:
        logger.error(f"Error creating topics: {e}")

    logger.info(f"Using topics: frames={FRAME_TOPIC}, detections={DETECTION_TOPIC}")

def delete_kafka_topics():
    """Delete the Kafka topics used for this run"""
    admin_client = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

    try:
        # Delete topics
        admin_client.delete_topics([FRAME_TOPIC, DETECTION_TOPIC])
        logger.info(f"Deleted Kafka topics: {FRAME_TOPIC}, {DETECTION_TOPIC}")
    except UnknownTopicOrPartitionError:
        logger.warning("Topics already deleted or don't exist")
    except Exception as e:
        logger.error(f"Error deleting topics: {e}")
