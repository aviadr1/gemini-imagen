#!/bin/bash
# Comprehensive Demo: Podcast Thumbnail Production Pipeline
# This demonstrates the full workflow using imagen CLI

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Imagen CLI - Comprehensive Demo"
echo "Scenario: Podcast Thumbnail Production"
echo "=========================================="
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up demo files..."
    rm -f /tmp/demo_*.png /tmp/demo_*.jpg /tmp/demo_*.json /tmp/demo_*.txt
    if [ -d "$DEMO_DIR" ]; then
        rm -rf "$DEMO_DIR"
    fi
    # Clean up test template
    uv run python -m gemini_imagen.cli.main template delete demo_podcast_thumb 2>/dev/null || true
    echo "Cleanup complete."
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Create demo directory
DEMO_DIR="/tmp/imagen_demo"
mkdir -p "$DEMO_DIR"

echo "📁 Working directory: $DEMO_DIR"
echo "📁 Project directory: $SCRIPT_DIR"
echo ""

# ==========================================
# PART 1: Basic Generation
# ==========================================
echo "=========================================="
echo "PART 1: Basic Image Generation"
echo "=========================================="
echo ""

echo "1️⃣  Generating a podcast thumbnail..."
uv run python -m gemini_imagen.cli.main generate \
    "A professional podcast thumbnail featuring bold typography with 'THE SHOW' text, \
microphone icon, vibrant colors, modern design" \
    -o "$DEMO_DIR/demo_base_thumbnail.png" \
    --aspect-ratio "16:9" \
    --temperature 0.7

echo ""
echo "✅ Generated: demo_base_thumbnail.png"
echo ""

# ==========================================
# PART 2: Image Analysis
# ==========================================
echo "=========================================="
echo "PART 2: Analyzing Generated Image"
echo "=========================================="
echo ""

echo "2️⃣  Analyzing what we generated..."
uv run python -m gemini_imagen.cli.main analyze "$DEMO_DIR/demo_base_thumbnail.png" > "$DEMO_DIR/demo_analysis.txt"

echo ""
echo "📊 Analysis saved to: demo_analysis.txt"
echo "--- Analysis excerpt ---"
head -n 5 "$DEMO_DIR/demo_analysis.txt"
echo "..."
echo ""

# ==========================================
# PART 3: Image Editing with Reference
# ==========================================
echo "=========================================="
echo "PART 3: Editing with Style Reference"
echo "=========================================="
echo ""

echo "3️⃣  Creating a variation with added guest photo..."
uv run python -m gemini_imagen.cli.main edit \
    "Keep the same style and layout but add space for a guest photo on the right side" \
    -i "$DEMO_DIR/demo_base_thumbnail.png" \
    --label "Original Design:" \
    -o "$DEMO_DIR/demo_thumbnail_v2.png" \
    --aspect-ratio "16:9"

echo ""
echo "✅ Generated variation: demo_thumbnail_v2.png"
echo ""

# ==========================================
# PART 4: Creating a Template
# ==========================================
echo "=========================================="
echo "PART 4: Creating Reusable Template"
echo "=========================================="
echo ""

echo "4️⃣  Creating a template for future episodes..."

# Create template JSON
cat > "$DEMO_DIR/podcast_template.json" <<'EOF'
{
  "prompt": "Professional podcast thumbnail with:\n- Show: {show_name}\n- Episode: {episode_number}\n- Guest: {guest_name}\n- Topic: {topic}\n\nStyle: Bold typography, vibrant colors, modern design with microphone icon",
  "system_prompt": "You are an expert graphic designer specializing in podcast thumbnails. Create eye-catching, professional designs.",
  "aspect_ratio": "16:9",
  "temperature": 0.7,
  "output_images": ["{output_path}"],
  "tags": ["podcast", "thumbnail", "demo"]
}
EOF

# Save the template
uv run python -m gemini_imagen.cli.main template save demo_podcast_thumb --from-json "$DEMO_DIR/podcast_template.json"

echo ""
echo "✅ Template 'demo_podcast_thumb' saved"
echo ""

# Show template details
echo "📋 Template details:"
uv run python -m gemini_imagen.cli.main template show demo_podcast_thumb

echo ""

# ==========================================
# PART 5: Using Template with Keys
# ==========================================
echo "=========================================="
echo "PART 5: Using Template for New Episode"
echo "=========================================="
echo ""

echo "5️⃣  Creating keys file for Episode 1..."

# Create keys for episode 1
cat > "$DEMO_DIR/episode1_keys.json" <<'EOF'
{
  "show_name": "Tech Talks Daily",
  "episode_number": "001",
  "guest_name": "Dr. Jane Smith",
  "topic": "AI Ethics and Society",
  "output_path": "/tmp/imagen_demo/demo_episode1_final.png"
}
EOF

echo "📄 Keys file created: episode1_keys.json"
echo ""

echo "6️⃣  Generating Episode 1 thumbnail using template..."
uv run python -m gemini_imagen.cli.main generate \
    --template demo_podcast_thumb \
    --keys "$DEMO_DIR/episode1_keys.json" \
    --dump-job > "$DEMO_DIR/episode1_job.json"

echo ""
echo "📋 Job preview saved to: episode1_job.json"
cat "$DEMO_DIR/episode1_job.json"
echo ""

echo "7️⃣  Actually generating Episode 1 thumbnail..."
uv run python -m gemini_imagen.cli.main generate \
    --template demo_podcast_thumb \
    --keys "$DEMO_DIR/episode1_keys.json"

echo ""
echo "✅ Generated: demo_episode1_final.png"
echo ""

# ==========================================
# PART 6: Fast Iteration with CLI Overrides
# ==========================================
echo "=========================================="
echo "PART 6: Fast Iteration with Overrides"
echo "=========================================="
echo ""

echo "8️⃣  Testing different guest for same episode..."
uv run python -m gemini_imagen.cli.main generate \
    --template demo_podcast_thumb \
    --keys "$DEMO_DIR/episode1_keys.json" \
    --var guest_name="Prof. John Doe" \
    --var output_path="/tmp/imagen_demo/demo_episode1_alt_guest.png" \
    --dry-run

echo ""
echo "✅ Dry-run complete (no image generated)"
echo ""

# ==========================================
# PART 7: Multiple Keys Files
# ==========================================
echo "=========================================="
echo "PART 7: Using Multiple Keys Files"
echo "=========================================="
echo ""

echo "9️⃣  Creating base keys and episode-specific keys..."

# Create base keys (shared across all episodes)
cat > "$DEMO_DIR/base_keys.json" <<'EOF'
{
  "show_name": "Tech Talks Daily",
  "output_path": "/tmp/imagen_demo/demo_output.png"
}
EOF

# Create episode 2 specific keys
cat > "$DEMO_DIR/episode2_keys.json" <<'EOF'
{
  "episode_number": "002",
  "guest_name": "Alice Johnson",
  "topic": "Quantum Computing Basics"
}
EOF

echo "📄 Created base_keys.json and episode2_keys.json"
echo ""

echo "🔟 Generating Episode 2 with multiple keys files..."
uv run python -m gemini_imagen.cli.main generate \
    --template demo_podcast_thumb \
    --keys "$DEMO_DIR/base_keys.json" \
    --keys "$DEMO_DIR/episode2_keys.json" \
    --var output_path="/tmp/imagen_demo/demo_episode2_final.png"

echo ""
echo "✅ Generated: demo_episode2_final.png"
echo ""

# ==========================================
# PART 8: Template Management
# ==========================================
echo "=========================================="
echo "PART 8: Template Management"
echo "=========================================="
echo ""

echo "1️⃣1️⃣  Listing all templates..."
uv run python -m gemini_imagen.cli.main template list

echo ""

echo "1️⃣2️⃣  Getting template path..."
TEMPLATE_PATH=$(uv run python -m gemini_imagen.cli.main template path demo_podcast_thumb)
echo "Template location: $TEMPLATE_PATH"
echo ""

# ==========================================
# PART 9: System Prompt from File
# ==========================================
echo "=========================================="
echo "PART 9: System Prompt from File"
echo "=========================================="
echo ""

echo "1️⃣3️⃣  Creating custom system prompt file..."
cat > "$DEMO_DIR/custom_system.txt" <<'EOF'
You are a world-class graphic designer who has created thumbnails for top podcasts.
Your designs are known for:
- Bold, eye-catching typography
- Perfect color harmony
- Professional composition
- Clear visual hierarchy

Create a thumbnail that stands out in a crowded feed.
EOF

echo "📄 Custom system prompt created"
echo ""

echo "1️⃣4️⃣  Generating with custom system prompt from file..."
uv run python -m gemini_imagen.cli.main generate \
    --template demo_podcast_thumb \
    --keys "$DEMO_DIR/episode1_keys.json" \
    -s "@$DEMO_DIR/custom_system.txt" \
    --var output_path="/tmp/imagen_demo/demo_custom_system.png"

echo ""
echo "✅ Generated with custom system prompt: demo_custom_system.png"
echo ""

# ==========================================
# PART 10: JSON Output Mode
# ==========================================
echo "=========================================="
echo "PART 10: JSON Output Mode"
echo "=========================================="
echo ""

echo "1️⃣5️⃣  Generating with JSON output..."
uv run python -m gemini_imagen.cli.main generate \
    "Quick test thumbnail" \
    -o "$DEMO_DIR/demo_json_test.png" \
    --json > "$DEMO_DIR/output.json"

echo ""
echo "📋 JSON output:"
cat "$DEMO_DIR/output.json"
echo ""

# ==========================================
# Summary
# ==========================================
echo "=========================================="
echo "Demo Complete! 🎉"
echo "=========================================="
echo ""
echo "Files created in $DEMO_DIR:"
ls -lh "$DEMO_DIR"
echo ""
echo "Template saved: demo_podcast_thumb"
echo ""
echo "What we demonstrated:"
echo "  ✅ Basic generation with options"
echo "  ✅ Image analysis"
echo "  ✅ Image editing with reference"
echo "  ✅ Template creation and management"
echo "  ✅ Template-based generation with keys"
echo "  ✅ CLI overrides for fast iteration"
echo "  ✅ Multiple keys files with precedence"
echo "  ✅ System prompt from file"
echo "  ✅ JSON output mode"
echo "  ✅ Dry-run and dump-job modes"
echo ""
echo "Cleanup will happen automatically on exit."
echo ""
