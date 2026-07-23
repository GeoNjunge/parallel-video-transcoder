#!/bin/sh

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

CONVERTER_SCRIPT="$SCRIPT_DIR/converter/parallel_convert.py"
BENCHMARK_SCRIPT="$SCRIPT_DIR/utils/benchmark.py"

show_help() {
    echo "Usage: ./run.sh [command] [path]"
    echo ""
    echo "Commands:"
    echo "  convert    Execute production parallel video conversion pipeline"
    echo "  benchmark  Execute single-threaded vs multi-process performance benchmarks"
    echo "  help       Display available options"
}

case "$1" in
    convert)
        echo "Launching Parallel Transcoder Pipeline..."
        python3 "$CONVERTER_SCRIPT" "${2:-.}"
        ;;
    benchmark)
        echo "Initializing Microbenchmarking Suite..."
        python3 "$BENCHMARK_SCRIPT" "${2:-.}"
        ;;
        
    *)
        show_help
        exit 1
        ;;
esac