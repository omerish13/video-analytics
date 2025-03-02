import os


def get_user_input():
    video_path = input("\nVideo path: ").strip()

    if not video_path:
        print("Error: Path cannot be empty. Please try again.")
        return get_user_input()

    if not video_path.endswith(('.mp4', '.avi', '.mov', '.mkv')):
        print("Warning: File might not be a video. Supported formats: .mp4, .avi, .mov, .mkv")
        confirm = input("Do you want to continue anyway? (y/n): ").lower()
        if confirm != 'y':
            return get_user_input()

    if not os.path.exists(video_path):
        print("Error: File not found. Please try again.")
        return get_user_input()

    return video_path

def get_video_path():
    print("\n=== Video Path Input ===")
    print("Please enter the path to your video file:")
    print("(Example: /path/to/your/video.mp4)")

    return get_user_input()
