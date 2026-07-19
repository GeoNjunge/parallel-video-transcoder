import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

# Configurations
DRIVE_PATH = "/home/ubuntu/projects/Album Downloader Python" 
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.m4v')
MAX_WORKERS = 2  # Hardcapped to your 2 physical cores

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

def process_single_video(file_path):
    """Worker function executed in parallel across cores."""
    start_time = time.time()
    filename = os.path.basename(file_path)
    temp_output = file_path + ".temp.mp4"
    
    # Check codec first to avoid unneeded work
    if check_codec(file_path) != "av1":
        return f"⏭️ Skipped (Not AV1): {filename}"

    # -threads 1 prevents ffmpeg from scaling past its assigned worker core
    cmd = [
        "nice", "-n", "19",
        "ffmpeg", "-y", "-i", file_path,
        "-threads", "1", 
        "-c:v", "libx264", 
        "-preset", "ultrafast", 
        "-profile:v", "main", 
        "-level", "3.1",
        "-c:a", "copy",
        temp_output
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        os.remove(file_path)         
        os.rename(temp_output, file_path) 
        elapsed = time.time() - start_time
        return f"✅ Successfully converted {filename} in {elapsed:.2f}s"
    except subprocess.CalledProcessError:
        if os.path.exists(temp_output):
            os.path.exists(temp_output) and os.remove(temp_output)
        return f"❌ Failed to convert: {filename}"

def main():
    if not os.path.exists(DRIVE_PATH):
        print(f"Error: Path {DRIVE_PATH} does not exist.")
        return

    print("🚀 Initializing HPC-style Parallel Video Processing Pipeline...")
    print(f"Target Path: {DRIVE_PATH} | Parallel Workers: {MAX_WORKERS}\n")
    
    # Discover all target files
    video_files = []
    for root, _, files in os.walk(DRIVE_PATH):
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                video_files.append(os.path.join(root, file))

    total_files = len(video_files)
    print(f"Found {total_files} total videos. Deploying workers...\n")

    global_start = time.time()
    
    # Process Pool Executor manages the 2 parallel worker processes
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_video, f): f for f in video_files}
        
        for i, future in enumerate(as_completed(futures), 1):
            result_message = future.result()
            print(f"[{i}/{total_files}] {result_message}")

    total_elapsed = time.time() - global_start
    print(f"\n🎉 Pipeline Complete! Total execution time: {total_elapsed:.2f} seconds.")

if __name__ == "__main__":
    main()
