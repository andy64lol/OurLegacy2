#!/bin/bash
# Convert PNG images to WebP format in game_data/assets

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$SCRIPT_DIR/game_data/assets"

if [ ! -d "$ASSETS_DIR" ]; then
    echo "Error: Assets directory not found at $ASSETS_DIR"
    exit 1
fi

echo "Starting PNG to WebP conversion in $ASSETS_DIR..."

# Counter for statistics
converted=0
skipped=0
errors=0

# Find and convert all PNG files
while IFS= read -r -d '' png_file; do
    # Get the base name without extension
    base_name="${png_file%.*}"
    webp_file="${base_name}.webp"
    
    # Check if WebP version already exists
    if [ -f "$webp_file" ]; then
        echo "⊘ Skipping (WebP exists): $(basename "$png_file")"
        ((skipped++))
        continue
    fi
    
    # Convert PNG to WebP using cwebp
    if command -v cwebp &> /dev/null; then
        if cwebp -quiet "$png_file" -o "$webp_file"; then
            echo "✓ Converted: $(basename "$png_file") → $(basename "$webp_file")"
            ((converted++))
        else
            echo "✗ Error converting: $(basename "$png_file")"
            ((errors++))
        fi
    elif command -v magick &> /dev/null; then
        # Fallback to ImageMagick if cwebp is not available
        if magick "$png_file" "$webp_file"; then
            echo "✓ Converted (ImageMagick): $(basename "$png_file") → $(basename "$webp_file")"
            ((converted++))
        else
            echo "✗ Error converting (ImageMagick): $(basename "$png_file")"
            ((errors++))
        fi
    else
        echo "✗ No image conversion tool found (cwebp or ImageMagick required)"
        exit 1
    fi
done < <(find "$ASSETS_DIR" -type f -name "*.png" -print0)

echo ""
echo "=========================================="
echo "Conversion Summary:"
echo "  Converted: $converted"
echo "  Skipped:   $skipped"
echo "  Errors:    $errors"
echo "=========================================="

if [ $errors -eq 0 ]; then
    echo "✓ All conversions completed successfully!"
    exit 0
else
    echo "✗ Some conversions failed"
    exit 1
fi
