## Setup & Execution Guide

### Prerequisites

Make sure `ffmpeg` and `ffprobe` are installed on your system.

* **Linux/WSL:**
```bash
sudo apt update && sudo apt install ffmpeg -y

```


* **macOS:**
```bash
brew install ffmpeg

```

### Quickstart

1. **Clone & Virtual Environment Setup**:
```bash
git clone https://github.com/GeoNjunge/parallel-video-transcoder.git
cd parallel-video-transcoder
python3 -m venv venv
source venv/bin/activate

```

2. **Grant Execution Permissions**:
```bash
chmod +x run.sh

```


3. **Usage via `run.sh**`:
* **Convert videos in a folder/USB**:
```bash
./run.sh convert /path/to/media/folder

```

* **Run system benchmark**:
```bash
./run.sh benchmark /path/to/media/folder

```




4. **Direct Python Execution**:
```bash
python3 converter/parallel_convert.py /path/to/media --workers 4

```