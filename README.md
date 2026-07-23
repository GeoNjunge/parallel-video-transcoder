# Parallel Video Transcoder

An HPC-inspired parallel video processing pipeline designed to eliminate hardware playback constraints on legacy smart TVs. This repository automates codec detection, structural filtering, and core-bounded hardware acceleration to convert modern, high-efficiency AV1 video streams down to universally compatible H.264 main profiles.

---

## The Origin: Digitizing Media for Dad's Legacy TV

This project originated from a real-world hardware incompatibility issue. My dad wanted to digitize his older video collection and convert downloaded files onto a FAT32 USB drive to watch on his living room TV. However, modern video downloaders frequently compress files using the newer **AV1 codec**. 

When plugged into my dad's legacy non-Android smart TV, every video threw a frustrating **"Unsupported Format"** error. 

Legacy television architectures rely on fixed-function Application-Specific Integrated Circuits (ASICs) designed long before AV1 hardware decoding existed. Unable to parse the AV1 bitstream, the TV rejected the files. To fix this without spending hours manually converting media files one by one, I built this parallel transcoding pipeline—transforming a restrictive hardware bottleneck into an optimized multi-core media processing showcase.

---

## Repository Architecture

```text
parallel-video-transcoder/
├── README.md                   # System design & project documentation
├── requirements.txt            # Minimal dependency footprint
├── run.sh                      # Shell-agnostic POSIX entry point
├── converter/
│   ├── batch_convert_to_h264.py # Naive sequential baseline script
│   └── parallel_convert.py     # Production parallel processing pipeline
└── utils/
    ├── benchmark.py            # Microarchitectural performance evaluation suite
    └── check_codec.py          # Fast metadata inspector wrapper

```

---

## Systems Engineering & Performance Architecture

Transcoding high-bitrate media across multiple video files can easily overwhelm low-core consumer CPUs or virtualized development environments (like WSL). This project solves hardware starvation through four core design decisions:

### 1. Process Isolation vs. Thread Thrashing

Standard single-instance FFmpeg commands attempt to spawn internal thread pools to saturate all detected CPU cores. Running multiple naive jobs concurrently causes severe kernel-level **Context Switching**—forcing the CPU to constantly flush L1/L2 caches to swap state.

This pipeline fixes thread thrashing by leveraging Python's `ProcessPoolExecutor` to spawn bounded worker processes corresponding to physical core counts, while explicitly locking each individual FFmpeg sub-process using the `-threads 1` flag. This guarantees core-level isolation and predictable throughput.

### 2. Bypassing Memory & Storage Bottlenecks

Writing transcode artifacts directly onto legacy storage media (e.g., USB 2.0/3.0 flash drives formatted in FAT32) introduces high **I/O Wait (`iowait`)** states, causing the CPU to sit idle waiting for write confirmations. The benchmarking suite routes volatile test conversions through `/tmp` (`tmpfs`), performing operations in system RAM to isolate CPU performance from storage write bottlenecks.

### 3. Early-Exit Stream Metadata Filtering

Before triggering expensive encoding operations, `utils/check_codec.py` executes lightweight inspection using `ffprobe`. It extracts structural header metadata directly from the container stream. Non-AV1 assets (or already compatible H.264 streams) trigger an immediate early exit, avoiding wasted processing cycles.

### 4. Zero-Copy Audio Stream Copying

Re-encoding audio requires decoding compressed bitstreams into raw PCM waveforms, calculating Fast Fourier Transforms (FFT), and re-compressing them. By specifying `-c:a copy` for standard audio tracks, raw audio packets are transferred byte-for-byte directly into the destination MP4 container without uncompression overhead.

---

## Quickstart & Setup

### Prerequisites

Ensure `ffmpeg` and `ffprobe` binaries are available in your system path.

* **Linux / Debian / WSL:**
```bash
sudo apt update && sudo apt install ffmpeg -y

```

* **macOS:**
```bash
brew install ffmpeg

```

### Installation

1. **Clone the repository:**
```bash
git clone [https://github.com/GeoNjunge/parallel-video-transcoder.git](https://github.com/GeoNjunge/parallel-video-transcoder.git)
cd parallel-video-transcoder

```

2. **Initialize Python virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate

```


3. **Set execution permissions:**
```bash
chmod +x run.sh

```
---

## Usage Instructions

Use the POSIX wrapper script (`run.sh`) to execute conversion or evaluation workloads:

```bash
# Run production parallel transcoding on a specific directory/USB path
./run.sh convert /path/to/media/folder

# Run microarchitectural benchmarking suite against an AV1 sample
./run.sh benchmark /path/to/media/folder

```

Alternatively, invoke Python directly with custom worker counts:

```bash
python3 converter/parallel_convert.py /path/to/media/folder --workers 4

```

---

## Benchmark & Performance Summary

Evaluated on a sample 480p AV1 dataset comparing sequential single-threaded processing against the core-bounded parallel pipeline:

| Metric | Sequential Baseline (1 Core) | Bounded Parallel Pipeline (2 Cores) |
| --- | --- | --- |
| **Wall-Clock Duration** | `120.45s` | `64.72s` |
| **Transcoding Throughput** | `~24.5 FPS` | `~45.6 FPS` |
| **Speedup Factor** | **1.0x (Baseline)** | **1.86x Faster** |

*Parallel scaling yields an ~93% hardware utilization efficiency over theoretical limits, with minimal loss attributed to Python process orchestration.*

```

```