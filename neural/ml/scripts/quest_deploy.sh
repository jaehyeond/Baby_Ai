#!/bin/bash
# Quest 3S Deployment Script — SmolVLM on-device inference
# Usage: bash quest_deploy.sh [push|run|benchmark|memory|cleanup]
#
# Prerequisites:
#   - Quest 3S connected via USB with developer mode enabled
#   - ADB authorized (accept prompt on headset)

set -euo pipefail

# --- Config ---
ADB="${ADB:-adb}"
QUEST_DIR="/data/local/tmp/llama.cpp"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ML_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOY_DIR="$ML_DIR/tools/quest-deploy"
MODELS_DIR="$ML_DIR/models_cache"
TEST_IMAGES_DIR="$ML_DIR/test_images"

# Models
MODEL_500M="SmolVLM-500M-Instruct-Q8_0.gguf"
MMPROJ_500M="mmproj-SmolVLM-500M-Instruct-Q8_0.gguf"
MODEL_256M="SmolVLM-256M-Instruct-Q8_0.gguf"
MMPROJ_256M="mmproj-SmolVLM-256M-Instruct-Q8_0.gguf"

# --- Functions ---

check_device() {
    echo "=== Checking ADB connection ==="
    local devices
    devices=$("$ADB" devices | grep -v "List" | grep -v "^$" | wc -l)
    if [ "$devices" -eq 0 ]; then
        echo "ERROR: No device connected. Connect Quest 3S via USB and enable developer mode."
        echo "  1. Quest: Settings > System > Developer > USB Debug ON"
        echo "  2. Connect USB-C cable"
        echo "  3. Accept ADB authorization on headset"
        exit 1
    fi
    echo "Device connected:"
    "$ADB" devices
    echo ""
    echo "Device info:"
    "$ADB" shell getprop ro.product.cpu.abi
    "$ADB" shell getprop ro.product.model
    "$ADB" shell getprop ro.build.version.sdk
    echo ""
    # Check available storage
    echo "Storage:"
    "$ADB" shell df /data/local/tmp | head -2
}

push_binaries() {
    echo "=== Pushing binaries to Quest ==="
    "$ADB" shell "mkdir -p $QUEST_DIR/bin $QUEST_DIR/lib $QUEST_DIR/models $QUEST_DIR/images"

    # Push stripped binaries
    echo "Pushing llama-mtmd-cli..."
    "$ADB" push "$DEPLOY_DIR/bin/llama-mtmd-cli" "$QUEST_DIR/bin/"
    "$ADB" shell "chmod +x $QUEST_DIR/bin/llama-mtmd-cli"

    # Push shared libraries
    echo "Pushing shared libraries..."
    for lib in "$DEPLOY_DIR/lib/"*.so; do
        "$ADB" push "$lib" "$QUEST_DIR/lib/"
    done
}

push_model() {
    local model_name="${1:-500M}"
    if [ "$model_name" = "500M" ]; then
        echo "=== Pushing SmolVLM-500M model ==="
        "$ADB" push "$MODELS_DIR/$MODEL_500M" "$QUEST_DIR/models/"
        "$ADB" push "$MODELS_DIR/$MMPROJ_500M" "$QUEST_DIR/models/"
    elif [ "$model_name" = "256M" ]; then
        echo "=== Pushing SmolVLM-256M model ==="
        "$ADB" push "$MODELS_DIR/$MODEL_256M" "$QUEST_DIR/models/"
        "$ADB" push "$MODELS_DIR/$MMPROJ_256M" "$QUEST_DIR/models/"
    else
        echo "ERROR: Unknown model: $model_name (use 500M or 256M)"
        exit 1
    fi
}

push_test_images() {
    echo "=== Pushing test images ==="
    for img in "$TEST_IMAGES_DIR/"*.jpg; do
        "$ADB" push "$img" "$QUEST_DIR/images/"
    done
}

run_inference() {
    local model_name="${1:-500M}"
    local image="${2:-images/01_table_objects.jpg}"
    local prompt="${3:-Describe what you see in this image.}"
    local ctx_size="${4:-2048}"

    if [ "$model_name" = "500M" ]; then
        local model_file="models/$MODEL_500M"
        local mmproj_file="models/$MMPROJ_500M"
    else
        local model_file="models/$MODEL_256M"
        local mmproj_file="models/$MMPROJ_256M"
    fi

    echo "=== Running inference (model=$model_name, ctx=$ctx_size) ==="
    echo "Image: $image"
    echo "Prompt: $prompt"
    echo ""

    "$ADB" shell "cd $QUEST_DIR && LD_LIBRARY_PATH=lib ./bin/llama-mtmd-cli \
        -m $model_file \
        --mmproj $mmproj_file \
        -c $ctx_size \
        --image $image \
        -p '$prompt' \
        --no-display-prompt \
        -n 256 \
        --temp 0.1 \
        2>&1"
}

run_benchmark() {
    local model_name="${1:-500M}"
    local num_runs="${2:-5}"
    local ctx_size="${3:-2048}"

    echo "=== Quest 3S Benchmark: SmolVLM-$model_name (${num_runs} runs) ==="
    echo "Timestamp: $(date -Iseconds)"
    echo ""

    if [ "$model_name" = "500M" ]; then
        local model_file="models/$MODEL_500M"
        local mmproj_file="models/$MMPROJ_500M"
    else
        local model_file="models/$MODEL_256M"
        local mmproj_file="models/$MMPROJ_256M"
    fi

    # Pre-benchmark device state
    echo "--- Device State (Pre) ---"
    "$ADB" shell "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 'thermal: N/A'"
    "$ADB" shell "dumpsys battery | grep -E 'level|temperature'"
    echo ""

    for i in $(seq 1 "$num_runs"); do
        echo "--- Run $i/$num_runs ---"

        "$ADB" shell "cd $QUEST_DIR && LD_LIBRARY_PATH=lib ./bin/llama-mtmd-cli \
            -m $model_file \
            --mmproj $mmproj_file \
            -c $ctx_size \
            --image images/01_table_objects.jpg \
            -p 'List all objects you can see in this image.' \
            --no-display-prompt \
            -n 128 \
            --temp 0.1 \
            2>&1" | grep -E "timing|total|eval|load|encoded"

        echo ""
        sleep 2
    done

    # Post-benchmark device state
    echo "--- Device State (Post) ---"
    "$ADB" shell "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 'thermal: N/A'"
    "$ADB" shell "dumpsys battery | grep -E 'level|temperature'"
}

measure_memory() {
    local model_name="${1:-500M}"

    if [ "$model_name" = "500M" ]; then
        local model_file="models/$MODEL_500M"
        local mmproj_file="models/$MMPROJ_500M"
    else
        local model_file="models/$MODEL_256M"
        local mmproj_file="models/$MMPROJ_256M"
    fi

    echo "=== Memory Measurement: SmolVLM-$model_name ==="
    echo ""
    echo "Starting inference in background and measuring PSS..."

    # Run inference in background on Quest
    "$ADB" shell "cd $QUEST_DIR && LD_LIBRARY_PATH=lib ./bin/llama-mtmd-cli \
        -m $model_file \
        --mmproj $mmproj_file \
        -c 2048 \
        --image images/01_table_objects.jpg \
        -p 'Describe every object you can see in detail including colors, materials, sizes, and spatial relationships.' \
        --no-display-prompt \
        -n 512 \
        --temp 0.1 \
        &" 2>/dev/null

    # Wait for model to load
    sleep 3

    # Sample memory multiple times
    for i in $(seq 1 10); do
        local pid
        pid=$("$ADB" shell "pidof llama-mtmd-cli" 2>/dev/null | tr -d '\r')
        if [ -n "$pid" ]; then
            echo "--- Sample $i (PID=$pid) ---"
            "$ADB" shell "cat /proc/$pid/smaps_rollup 2>/dev/null || cat /proc/$pid/status | grep -E 'VmRSS|VmPeak|VmSize'"
            echo ""
        else
            echo "Process exited at sample $i"
            break
        fi
        sleep 2
    done

    echo "=== System memory after inference ==="
    "$ADB" shell "cat /proc/meminfo | head -5"
}

cleanup() {
    echo "=== Cleaning up Quest deployment ==="
    "$ADB" shell "rm -rf $QUEST_DIR"
    echo "Removed $QUEST_DIR"
}

status() {
    echo "=== Quest Deployment Status ==="
    "$ADB" shell "ls -la $QUEST_DIR/ 2>/dev/null || echo 'Not deployed'"
    echo ""
    "$ADB" shell "ls -lh $QUEST_DIR/bin/ 2>/dev/null || echo 'No binaries'"
    echo ""
    "$ADB" shell "ls -lh $QUEST_DIR/models/ 2>/dev/null || echo 'No models'"
    echo ""
    "$ADB" shell "ls -lh $QUEST_DIR/images/ 2>/dev/null || echo 'No images'"
}

# --- Main ---
case "${1:-help}" in
    check)
        check_device
        ;;
    push)
        check_device
        push_binaries
        push_model "${2:-500M}"
        push_test_images
        echo ""
        echo "=== Deployment complete ==="
        status
        ;;
    run)
        run_inference "${2:-500M}" "${3:-images/01_table_objects.jpg}" "${4:-Describe what you see in this image.}" "${5:-2048}"
        ;;
    benchmark)
        run_benchmark "${2:-500M}" "${3:-5}" "${4:-2048}"
        ;;
    memory)
        measure_memory "${2:-500M}"
        ;;
    status)
        status
        ;;
    cleanup)
        cleanup
        ;;
    help|*)
        echo "Quest 3S SmolVLM Deployment Tool"
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  check                    Check ADB connection and device info"
        echo "  push [500M|256M]         Push binaries + model + test images to Quest"
        echo "  run [500M|256M] [image] [prompt] [ctx]  Run single inference"
        echo "  benchmark [500M|256M] [runs] [ctx]      Run latency benchmark"
        echo "  memory [500M|256M]       Measure PSS/RSS memory usage"
        echo "  status                   Show deployment status on Quest"
        echo "  cleanup                  Remove all files from Quest"
        echo ""
        echo "Examples:"
        echo "  $0 check"
        echo "  $0 push 500M"
        echo "  $0 run 500M images/01_table_objects.jpg 'What objects are here?'"
        echo "  $0 benchmark 500M 5"
        echo "  $0 memory 500M"
        ;;
esac
