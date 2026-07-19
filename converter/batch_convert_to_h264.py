import os
import subprocess

# Update this to your exact USB drive path
DRIVE_PATH = "." 
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.m4v')

def check_codec(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"

def convert_to_h264(file_path):
    temp_output = file_path + ".temp.mp4"
    print(f"Converting: {os.path.basename(file_path)}")
    
    # -c:v libx264 forces H.264 video encoding
    # -c:a copy copies the existing audio without re-encoding to save time
    cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-c:v", "libx264", "-profile:v", "main", "-level", "3.1",
        "-c:a", "aac", "-b:a", "128k",
        temp_output
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        os.remove(file_path)         # Remove old AV1 file
        os.rename(temp_output, file_path) # Rename temp file to original name
        print(f"Success!")
    except subprocess.CalledProcessError:
        print(f"Failed to convert {file_path}")
        if os.path.exists(temp_output):
            os.remove(temp_output)

def fix_usb_videos(root_dir):
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                file_path = os.path.join(root, file)
                codec = check_codec(file_path)
                
                if codec == "av1":
                    convert_to_h264(file_path)

if __name__ == "__main__":
    if os.path.exists(DRIVE_PATH):
        print("Starting video conversion process...")
        fix_usb_videos(DRIVE_PATH)
        print("All AV1 videos have been converted to H.264!")
    else:
        print(f"Directory {DRIVE_PATH} not found.")
