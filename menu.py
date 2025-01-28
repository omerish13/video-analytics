def get_video_path():
    print("\n=== Video Path Input ===")
    print("Please enter the path to your video file:")
    print("(Example: /path/to/your/video.mp4)")
    
    while True:
        video_path = input("\nVideo path: ").strip()
        
        if not video_path:
            print("Error: Path cannot be empty. Please try again.")
            continue
            
        if not video_path.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            print("Warning: File might not be a video. Supported formats: .mp4, .avi, .mov, .mkv")
            confirm = input("Do you want to continue anyway? (y/n): ").lower()
            if confirm != 'y':
                continue
                
        return video_path