#!/bin/bash
# prepare_archive_for_sharing.sh
# Usage: ./prepare_archive_for_sharing.sh <archive_name>
# Example: ./prepare_archive_for_sharing.sh colorado_beetle_on_green_leave

ARCHIVE_NAME="$1"
ARCHIVE_DIR="./archives/${ARCHIVE_NAME}"

if [ ! -d "$ARCHIVE_DIR" ]; then
    echo "Archive directory $ARCHIVE_DIR does not exist."
    exit 1
fi

echo "WARNING: This operation will delete all files in $ARCHIVE_DIR that are not compressed (.tar.gz)."
echo "Before proceeding, the script will check that every .yuv file in the archive has a corresponding .tar.gz file."
read -p "Are you sure you want to continue? (y/n): " answer
if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
    echo "Operation cancelled."
    exit 0
fi

# Check that each .yuv file has a corresponding .tar.gz file.
ALL_COMPRESSED=true
for yuv_file in "$ARCHIVE_DIR"/*.yuv; do
    # If no .yuv files exist, skip.
    [ -e "$yuv_file" ] || continue
    base=$(basename "$yuv_file" .yuv)
    compressed_file="$ARCHIVE_DIR/${base}.tar.gz"
    if [ ! -f "$compressed_file" ]; then
        echo "Error: Compressed version not found for $yuv_file (expected $compressed_file)."
        ALL_COMPRESSED=false
    fi
done

if [ "$ALL_COMPRESSED" = false ]; then
    echo "Not all .yuv files have a corresponding compressed version. Aborting."
    exit 1
fi

# If all checks passed, remove all files that are NOT .tar.gz.
find "$ARCHIVE_DIR" -type f ! -name "*.tar.gz" -delete
echo "Archive prepared for sharing: only compressed (.tar.gz) files remain in $ARCHIVE_DIR."

