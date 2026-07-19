import os
import subprocess

# Update this to your drive's path, e.g., 'D:\\' or '/Volumes/MyUSB'
DRIVE_PATH = "." 
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.m4v')

def get_video_info(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return ["Unknown", "Unknown", "Unknown"]

def scan_drive(root_dir):
    print(f"Scanning {root_dir} for video files...\n")
    print(f"{'FILE PATH':<50} | {'CODEC':<10} | {'RESOLUTION'}")
    print("-" * 75)

    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                file_path = os.path.join(root, file)
                info = get_video_info(file_path)
                
                # Handling ffprobe output
                if len(info) >= 3:
                    codec, width, height = info[0], info[1], info[2]
                    resolution = f"{width}x{height}"
                else:
                    codec, resolution = "Error", "Error"
                    
                print(f"{file:<50} | {codec:<10} | {resolution}")

if __name__ == "__main__":
    if os.path.exists(DRIVE_PATH):
        scan_drive(DRIVE_PATH)
    else:
        print(f"Directory {DRIVE_PATH} does not exist. Please check the drive letter/path.")
