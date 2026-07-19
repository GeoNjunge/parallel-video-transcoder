## parallel-video-transcoder
***An HPC-inspired parallel video processing pipeline built to bypass legacy hardware limitations for my dad's old TV.***

* The Problem: Legacy TV hardware constraints vs. modern media scraping tools pulling AV1 streams. Parental UX frustration (The Cassette-to-Digital bottleneck).
* The Constraint Profile: System running on limited hardware resources (2 CPU cores, slow I/O bound FAT32 external file storage).
* The Optimization Journey:
1. Baseline: Single-threaded sequential execution bound by heavy CPU encoding mechanics.
   1. Iteration 1: Codec filtering (ffprobe) to prevent re-encoding already compatible streams.
   2. Iteration 2: Tuning parameters via FFmpeg optimization primitives (-preset ultrafast, -c:a copy to completely bypass audio re-encoding).
   3. Final Architecture: Implementing an explicit Python concurrent worker pool, establishing process limits, and enforcing -threads 1 boundary isolation to prevent CPU thrashing. [1] 