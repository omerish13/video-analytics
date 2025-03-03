import hashlib
import os
import time
import asyncio
from nats.aio.client import Client as NATS
from utils.menu import get_video_path
from utils.logger import logger

# Configuration
NATS_SERVER = 'nats://localhost:4222'
VIDEO_PATH = get_video_path()  # Path to your video file
DETECTION_THRESHOLD = 5000  # Adjust sensitivity of motion detection
BLUR_AMOUNT = 15  # Higher values mean more blur
OUTPUT_VIDEO_PATH = 'processed_video.mp4'  # Temporary output file

# Generate unique file storage path for this run
RUN_ID = hashlib.md5(f"{VIDEO_PATH}_{time.time()}".encode()).hexdigest()[:8]
TEMP_DIR = f"temp_frames_{RUN_ID}"

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)

# Generate unique stream names based on the video file
def generate_stream_names(video_path):
    """Generate unique stream names based on the video file path"""
    # Create a unique hash based on the video path and current timestamp
    hash_input = f"{video_path}_{time.time()}"
    hash_obj = hashlib.md5(hash_input.encode())
    hash_str = hash_obj.hexdigest()[:8]  # Use first 8 chars of hash

    # Get video filename without extension
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # Create safe stream names
    safe_name = ''.join(c if c.isalnum() else '_' for c in video_name)

    # Create unique stream names
    frame_stream = f"frames_{safe_name}_{hash_str}"
    detection_stream = f"detections_{safe_name}_{hash_str}"

    return frame_stream, detection_stream

# Generate the stream names for this run
FRAME_STREAM, DETECTION_STREAM = generate_stream_names(VIDEO_PATH)

# Global flag for signaling completion
processing_complete = False

# Shared event loop for async operations
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def setup_nats_connection():
    """Create a connection to NATS"""
    # Setup connection with reasonable defaults
    nc = NATS()
    options = {
        'servers': [NATS_SERVER],
        'reconnect_time_wait': 5,
        'max_reconnect_attempts': 10,
        'ping_interval': 20,  # More frequent pings to maintain connection
        'allow_reconnect': True
    }
    await nc.connect(**options)
    return nc
async def setup_jetstream(nc):
    """Get JetStream context from NATS connection"""
    js = nc.jetstream()
    return js

async def setup_streams():
    """Create JetStream streams for this video processing run"""
    nc = await setup_nats_connection()
    js = await setup_jetstream(nc)

    # Create streams with memory storage for speed
    try:
        # Create frame stream - for smaller metadata
        await js.add_stream(
            name=FRAME_STREAM,
            subjects=[f"{FRAME_STREAM}.*"],
            max_msgs_per_subject=10000,  # Limit messages per subject
            discard="old"  # Discard old messages if limit is reached
        )
        logger.info(f"Created frame stream: {FRAME_STREAM}")

        # Create detection stream
        await js.add_stream(
            name=DETECTION_STREAM,
            subjects=[f"{DETECTION_STREAM}.*"],
            max_msgs_per_subject=10000,
            discard="old"
        )
        logger.info(f"Created detection stream: {DETECTION_STREAM}")
    except Exception as e:
        logger.error(f"Error creating streams: {e}")

    await nc.close()
    logger.info(f"Using streams: frames={FRAME_STREAM}, detections={DETECTION_STREAM}")

async def delete_streams():
    """Delete the JetStream streams used for this run"""
    try:
        nc = await setup_nats_connection()
        js = await setup_jetstream(nc)

        # Delete streams
        await js.delete_stream(FRAME_STREAM)
        await js.delete_stream(DETECTION_STREAM)
        logger.info(f"Deleted streams: {FRAME_STREAM}, {DETECTION_STREAM}")

        await nc.close()
    except Exception as e:
        logger.error(f"Error deleting streams: {e}")

def clean_temp_files():
    """Clean up temporary frame files"""
    try:
        for filename in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
        os.rmdir(TEMP_DIR)
        logger.info(f"Cleaned up temporary directory {TEMP_DIR}")
    except Exception as e:
        logger.error(f"Error cleaning temporary files: {e}")

def setup_nats_streams_sync():
    """Synchronous wrapper to set up NATS streams"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_streams())

def delete_nats_streams_sync():
    """Synchronous wrapper to delete NATS streams"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(delete_streams())
