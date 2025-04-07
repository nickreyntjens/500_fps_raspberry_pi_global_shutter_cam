#!/bin/bash
# capture_and_archive.sh
# First make this file executable: chmod +x capture_and_archive.sh
# Usage: ./capture_and_archive.sh <archive_name> <width> <height> <framerate> <capture_time_ms>
# Example: ./capture_and_archive.sh colorado_beetle_on_green_leave 224 96 536 20000

# --- Step 0: Ensure a RAM disk is mounted ---
RAMDISK="/dev/shm"
if ! mountpoint -q "$RAMDISK"; then
    echo "$RAMDISK is not mounted. Attempting to mount a tmpfs of size 500MB..."
    # Create the directory if it does not exist.
    [ -d "$RAMDISK" ] || sudo mkdir -p "$RAMDISK"
    # Mount tmpfs on it with a maximum size of 500MB.
    sudo mount -t tmpfs -o size=500M tmpfs "$RAMDISK"
    if [ $? -ne 0 ]; then
        echo "Failed to mount tmpfs on $RAMDISK. Exiting."
        exit 1
    fi
fi
echo "Using RAM disk at: $RAMDISK"

# --- Parameters ---
ARCHIVE_NAME="$1"
WIDTH="$2"
HEIGHT="$3"
FRAMERATE="$4"
CAPTURE_TIME="$5"  # in milliseconds

# Validate required parameters.
if [ -z "$ARCHIVE_NAME" ] || [ -z "$WIDTH" ] || [ -z "$HEIGHT" ] || [ -z "$FRAMERATE" ] || [ -z "$CAPTURE_TIME" ]; then
    echo "Usage: ./capture_and_archive.sh <archive_name> <width> <height> <framerate> <capture_time_ms>"
    exit 1
fi

# Create a timestamp for file names (e.g., 20230428-142530)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Base filename includes width, height, framerate, and timestamp.
BASENAME="captured_${WIDTH}x${HEIGHT}_${FRAMERATE}fps_${TIMESTAMP}"
YUV_FILE="${RAMDISK}/${BASENAME}.yuv"
MP4_FILE="${RAMDISK}/${BASENAME}.mp4"
TAR_FILE="${RAMDISK}/${BASENAME}.tar.gz"

# --- Step 1: Capture YUV Video ---
echo "Capturing YUV video..."
chmod +x GScrop
./GScrop "$WIDTH" "$HEIGHT" "$FRAMERATE" 32
rpicam-vid --no-raw --codec yuv420 --width "$WIDTH" --height "$HEIGHT" --denoise cdn_off --framerate "$FRAMERATE" -t "$CAPTURE_TIME" -o - 2>/dev/null > "$YUV_FILE"
echo "Captured YUV video to: $YUV_FILE"

# --- Step 2: Convert YUV to MP4 ---
# Calculate padded dimensions:
# Next multiple of 64 for width, and next multiple of 16 for height.
PAD_WIDTH=$(( (WIDTH + 63) / 64 * 64 ))
PAD_HEIGHT=$(( (HEIGHT + 15) / 16 * 16 ))

echo "Using padded dimensions: ${PAD_WIDTH}x${PAD_HEIGHT} for ffmpeg (source of trouble!)"
echo "Converting captured YUV to MP4..."
cat "$YUV_FILE" | ffmpeg -f rawvideo -vcodec rawvideo -s "${PAD_WIDTH}x${PAD_HEIGHT}" -r "$FRAMERATE" -pix_fmt yuv420p -i - \
    -c:v libx264 -preset slow -qp 0 -y "$MP4_FILE" -loglevel quiet
echo "Converted MP4 video stored at: $MP4_FILE"

# --- Step 3: Archive Files ---
# Create a permanent archive directory under ./archives/<archive_name>
ARCHIVE_DIR="./archives/${ARCHIVE_NAME}"
mkdir -p "$ARCHIVE_DIR"

# Copy the raw YUV and MP4 files into the archive.
cp "$YUV_FILE" "$ARCHIVE_DIR/"
cp "$MP4_FILE" "$ARCHIVE_DIR/"

# Create a tar.gz archive of the YUV file.
tar -czf "${ARCHIVE_DIR}/${BASENAME}.tar.gz" -C "$RAMDISK" "${BASENAME}.yuv"
echo "Archived captured files to directory: $ARCHIVE_DIR"

echo "Capture and archiving complete."

