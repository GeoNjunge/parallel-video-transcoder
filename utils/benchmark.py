import argparse
import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.m4v')
TEMP_OUT_DIR = "/tmp/transcode_bench"

def find_first_av1_file(root_dir: str):
    """Locates an AV1 video sample to run throughput benchmarks against."""
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                file_path = os.path.join(root, file)
                cmd = [
                    "ffprobe", "-v", "error", "-select_streams", "v:0", 
                    "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", 
                    file_path
                ]
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    if res.stdout.strip() == "av1":
                        return file_path
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
    return None

def get_frame_count(file_path: str) -> int:
    """Extracts total video frame count to measure processing throughput (FPS)."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", 
        "-show_entries", "stream=nb_frames", "-of", "default=noprint_wrappers=1:nokey=1", 
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(res.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 500  # Default fallback frame count estimate

def run_ffmpeg(file_path: str, output_path: str, threads: int = 1):
    """Executes FFmpeg transcoding with bounded core thread limits."""
    cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-threads", str(threads),
        "-c:v", "libx264", "-preset", "ultrafast", "-profile:v", "main", "-level", "3.1",
        "-c:a", "copy", output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def main():
    parser = argparse.ArgumentParser(description="Transcoder Microbenchmark Suite")
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan for AV1 test sample")
    args = parser.parse_args()

    os.makedirs(TEMP_OUT_DIR, exist_ok=True)
    test_file = find_first_av1_file(os.path.abspath(args.path))
    
    if not test_file:
        print("Error: No AV1 sample video found to execute benchmarks.")
        return

    print(f"Target Test File: {os.path.basename(test_file)}")
    total_frames = get_frame_count(test_file)
    
    out1 = os.path.join(TEMP_OUT_DIR, "bench_seq1.mp4")
    out2 = os.path.join(TEMP_OUT_DIR, "bench_seq2.mp4")
    
    # Run 1: Sequential Execution (1 Core)
    print("\n[1/2] Running Benchmark: Sequential Baseline (1 Worker Thread)...")
    start_seq = time.time()
    run_ffmpeg(test_file, out1, threads=1)
    run_ffmpeg(test_file, out2, threads=1)
    seq_duration = time.time() - start_seq
    seq_fps = (total_frames * 2) / seq_duration
    print(f"Sequential Execution Time: {seq_duration:.2f}s ({seq_fps:.1f} FPS)")

    for path in (out1, out2):
        if os.path.exists(path):
            os.remove(path)

    # Run 2: Core-Bounded Parallel Pipeline (2 Workers)
    print("\n[2/2] Running Benchmark: Parallel Pipeline (2 Worker Processes)...")
    start_para = time.time()
    
    with ProcessPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_ffmpeg, test_file, out1, 1)
        f2 = executor.submit(run_ffmpeg, test_file, out2, 1)
        f1.result()
        f2.result()
            
    para_duration = time.time() - start_para
    para_fps = (total_frames * 2) / para_duration
    print(f"Parallel Execution Time:   {para_duration:.2f}s ({para_fps:.1f} FPS)")

    for path in (out1, out2):
        if os.path.exists(path):
            os.remove(path)

    # Performance Metrics
    speedup = seq_duration / para_duration
    efficiency = (speedup / 2) * 100
    
    print("\n" + "=" * 50)
    print("PERFORMANCE ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"• Total Speedup Factor  : {speedup:.2f}x faster")
    print(f"• Parallel Efficiency   : {efficiency:.1f}% hardware utilization")
    print(f"• Throughput Delta      : +{para_fps - seq_fps:.1f} FPS")
    print("=" * 50)

if __name__ == "__main__":
    main()