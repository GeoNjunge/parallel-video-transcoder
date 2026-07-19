#!/bin/sh

# Determine the absolute directory where this shell script lives
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

CONVERTER_SCRIPT="$SCRIPT_DIR/converter/parallel_converter.py"
BENCHMARK_SCRIPT="$SCRIPT_DIR/utils/benchmark.py"

show_help() {
    echo "Usage: ./run.sh [command]"
    echo ""
    echo "Commands:"
    echo "  convert    Execute the production parallel H.264 video conversion pipeline"
    echo "  benchmark  Execute the multi-threaded vs single-threaded HPC performance run"
    echo "  help       Display available command matrix interfaces"
}

case "$1" in
    convert)
        echo "🚀 Launching Parallel Production Transcoder Pipeline..."
        python3 "$CONVERTER_SCRIPT"
        ;;
    benchmark)
        echo "📊 Initializing Microarchitectural Evaluation Suite..."
        python3 "$BENCHMARK_SCRIPT"
        ;;
    *)
        show_help
        exit 1
        ;;
esac
