import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor

# Configurations
DRIVE_PATH = "." 
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.m4v')
TEMP_OUT_DIR = "/tmp/transcode_bench"

def find_first_av1_file(root_dir):
    """Finds a single AV1 video file to use as the benchmark test subject."""
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                file_path = os.path.join(root, file)
                # Check codec via ffprobe
                cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", 
                       "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    if res.stdout.strip() == "av1":
                        return file_path
                    if res.stdout.strip() == "av1":
                        return file_path
                except subprocess.CalledProcessError:
                    continue
    return None

def get_frame_count(file_path):
    """Gets total frames in the video to calculate FPS throughput."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", 
           "-show_entries", "stream=nb_frames", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(res.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 500 # Fallback estimate if stream metadata lacks frame count

def run_ffmpeg(file_path, output_path, threads=1):
    """Executes the exact FFmpeg transcode configuration."""
    cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-threads", str(threads),
        "-c:v", "libx264", "-preset", "ultrafast", "-profile:v", "main", "-level", "3.1",
        "-c:a", "copy", output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def main():
    os.makedirs(TEMP_OUT_DIR, exist_ok=True)
    test_file = find_first_av1_file(DRIVE_PATH)
    
    if not test_file:
        print("Error: No AV1 files found on the drive to run benchmarks against.")
        return

    print(f"Target Test File: {os.path.basename(test_file)}")
    total_frames = get_frame_count(test_file)
    
    # Define workload: Transcoding 2 instances of this file
    out1 = os.path.join(TEMP_OUT_DIR, "bench_seq1.mp4")
    out2 = os.path.join(TEMP_OUT_DIR, "bench_seq2.mp4")
    
    # ----------------------------------------------------
    # RUN 1: Sequential Baseline (1 Thread, 1 File at a time)
    # ----------------------------------------------------
    print("\n Running Benchmark 1: Sequential Baseline (1 Core)...")
    start_seq = time.time()
    run_ffmpeg(test_file, out1, threads=1)
    run_ffmpeg(test_file, out2, threads=1)
    end_seq = time.time()
    seq_duration = end_seq - start_seq
    seq_fps = (total_frames * 2) / seq_duration
    print(f"⏱️  Sequential Total Time: {seq_duration:.2f}s ({seq_fps:.1f} FPS)")

    # Clean up output artifacts
    os.remove(out1); os.remove(out2)

    # ----------------------------------------------------
    # RUN 2: Parallel Architecture (2 Workers, Bounded Threads)
    # ----------------------------------------------------
    print("\n Running Benchmark 2: Core-Bounded Parallel Pipeline (2 Cores Concurrent)...")
    start_para = time.time()
    
    with ProcessPoolExecutor(max_workers=2) as executor:
        # Launch two transcoding tasks simultaneously
        futures = [
            executor.submit(run_ffmpeg, test_file, out1, 1),
            executor.submit(run_ffmpeg, test_file, out2, 2)
        ]
        for future in futures:
            future.result()
            
    end_para = time.time()
    para_duration = end_para - start_para
    para_fps = (total_frames * 2) / para_duration
    print(f"Parallel Total Time: {para_duration:.2f}s ({para_fps:.1f} FPS)")

    # Final Cleanup
    os.path.exists(out1) and os.remove(out1)
    os.path.exists(out2) and os.remove(out2)

    # ----------------------------------------------------
    # Metric Synthesis
    # ----------------------------------------------------
    speedup = seq_duration / para_duration
    efficiency = (speedup / 2) * 100 # Multiplier over number of cores
    
    print("\n" + "="*50)
    print("PERFORMANCE ANALYSIS SUMMARY")
    print("="*50)
    print(f"• Total Speedup Factor  : {speedup:.2f}x faster")
    print(f"• Parallel Efficiency   : {efficiency:.1f}% hardware utilization")
    print(f"• Throughput Delta      : +{para_fps - seq_fps:.1f} FPS")
    print("="*50)

if __name__ == "__main__":
    main()
