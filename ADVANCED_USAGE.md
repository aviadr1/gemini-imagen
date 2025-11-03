# Advanced Usage Guide

This guide covers advanced features and use cases for gemini-imagen, including S3 integration, LangSmith tracing, batch processing, and scripting.

## Table of Contents

- [S3 Integration](#s3-integration)
- [LangSmith Tracing](#langsmith-tracing)
- [Scripting and Automation](#scripting-and-automation)
- [Safety Settings](#safety-settings)
- [Performance Optimization](#performance-optimization)
- [Advanced CLI Usage](#advanced-cli-usage)

## S3 Integration

### Setup

Install with S3 support:

```bash
pip install gemini-imagen[s3]
```

Configure AWS credentials:

```bash
# Using CLI
imagen keys set aws-access-key YOUR_ACCESS_KEY
imagen keys set aws-secret-key YOUR_SECRET_KEY
imagen config set aws_storage_bucket_name YOUR_BUCKET

# Or using environment variables
export GV_AWS_ACCESS_KEY_ID=your_aws_access_key
export GV_AWS_SECRET_ACCESS_KEY=your_aws_secret_key
export GV_AWS_STORAGE_BUCKET_NAME=your-bucket-name
```

### Python API

```python
from gemini_imagen import GeminiImageGenerator

generator = GeminiImageGenerator()

# Input from S3, output to S3
result = await generator.generate(
    prompt="Enhance this architectural photo",
    input_images=["s3://my-bucket/input.jpg"],
    output_images=["s3://my-bucket/enhanced.jpg"]
)

# Access S3 URIs and HTTP URLs
print(f"S3 URI: {result.image_s3_uri}")
print(f"HTTP URL: {result.image_http_url}")
```

### CLI Usage

```bash
# Input from S3, output to S3
imagen generate "enhance this" -i s3://bucket/input.jpg -o s3://bucket/output.jpg

# Upload/download
imagen upload local.png s3://bucket/remote.png
imagen download s3://bucket/remote.png local.png

# Mixed local and S3
imagen generate "blend these" -i local.jpg -i s3://bucket/style.jpg -o s3://bucket/result.jpg
```

### Workflow Example

```bash
# Download from S3, process locally, upload back
imagen download s3://bucket/original.png local.png
imagen edit "make it brighter" -i local.png -o edited.png
imagen upload edited.png s3://bucket/edited.png
```

## LangSmith Tracing

LangSmith provides observability for debugging and monitoring your image generation workflows.

### Setup

```bash
# Using environment variables
export LANGSMITH_API_KEY=your_langsmith_api_key
export LANGSMITH_PROJECT=your_project_name
export LANGSMITH_TRACING=true

# Or using CLI
imagen config set langsmith_api_key YOUR_KEY
imagen config set langsmith_project my-project
imagen config set langsmith_tracing true
```

### Python API

```python
import os
from gemini_imagen import GeminiImageGenerator

# Enable tracing
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "your-key"

generator = GeminiImageGenerator(log_images=True)

result = await generator.generate(
    prompt="A robot reading in a cozy library",
    output_images=["robot_library.png"],
    metadata={"user_id": "demo", "session": "example"},
    tags=["demo", "robot", "library"]
)

# View traces at https://smith.langchain.com/
```

### CLI Usage

```bash
# Enable tracing for a single command
imagen generate "a robot" -o robot.png --trace --tag experiment --tag v1

# Enable globally
imagen config set langsmith_tracing true

# All subsequent commands will be traced
imagen generate "a cat" -o cat.png
```

### What Gets Logged

- Input prompts and parameters
- Model used
- Generated images (as S3 URLs if available)
- Text responses
- Metadata and tags
- Execution time
- Safety filtering information (if blocked)

## Scripting and Automation

### Batch Image Generation

```bash
#!/bin/bash
# generate_batch.sh

# Read prompts from file
while IFS= read -r prompt; do
  # Generate filename from prompt
  filename=$(echo "$prompt" | tr ' ' '_' | tr '[:upper:]' '[:lower:]').png

  # Generate image
  echo "Generating: $filename"
  imagen generate "$prompt" -o "$filename" --json | jq '.image_path'

  # Optional: Upload to S3
  imagen upload "$filename" "s3://my-bucket/generated/$filename"
done < prompts.txt
```

### Multiple Variations

```bash
# Generate 3 variations with different temperatures
for i in {1..3}; do
  temp=$(echo "scale=1; 0.3 * $i" | bc)
  imagen generate "abstract art" -o "art_${i}.png" --temperature "$temp"
done
```

### Batch Image Analysis

```bash
# Analyze all images in a directory
for img in *.jpg; do
  echo "Analyzing $img..."
  imagen analyze "$img" > "${img%.jpg}_description.txt"
done
```

### Style Transfer Pipeline

```bash
#!/bin/bash
# style_transfer.sh

# Download style reference
imagen download s3://styles/monet.jpg style.jpg

# Apply style to multiple photos
for photo in photos/*.jpg; do
  output="styled_$(basename $photo)"
  imagen edit "apply this artistic style" \
    -i "$photo" --label "Original:" \
    -i style.jpg --label "Style:" \
    -o "$output"
done
```

### Quality Control Workflow

```bash
#!/bin/bash
# generate_and_verify.sh

prompt="$1"

# Generate image
imagen generate "$prompt" -o output.png

# Analyze to verify it matches prompt
description=$(imagen analyze output.png \
  -p "Does this image match: $prompt?" \
  --json | jq -r '.description')

echo "Generated image"
echo "Verification: $description"
```

## Safety Settings

### Global Configuration

```bash
# Set default safety level
imagen config set safety_settings relaxed  # Least restrictive
imagen config set safety_settings default  # Moderate
imagen config set safety_settings strict   # Most restrictive
imagen config set safety_settings none     # Minimal filtering
```

### Per-Generation Override (CLI)

```bash
# Use a preset
imagen generate "artistic photo" -o output.png --safety-setting preset:relaxed

# Set specific category
imagen generate "portrait" -o output.png \
  --safety-setting SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH

# Multiple categories
imagen generate "artwork" -o output.png \
  --safety-setting SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH \
  --safety-setting DANGEROUS_CONTENT:BLOCK_LOW_AND_ABOVE
```

### Python API

```python
from gemini_imagen import GeminiImageGenerator, SafetySetting, HarmCategory, HarmBlockThreshold

generator = GeminiImageGenerator()

# Relaxed settings for artistic content
relaxed_settings = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
    )
]

result = await generator.generate(
    prompt="A tasteful artistic nude statue",
    output_images=["output.png"],
    safety_settings=relaxed_settings
)
```

For more details, see [docs/SAFETY_FILTERING.md](docs/SAFETY_FILTERING.md).

## Performance Optimization

### Parallel Loading and Saving

The library automatically parallelizes I/O operations for multiple images using `asyncio.gather`:

```python
# This automatically loads all 5 images in parallel
result = await generator.generate(
    prompt="Combine these architectural styles",
    input_images=[
        "https://example.com/building1.jpg",  # All download
        "https://example.com/building2.jpg",  # simultaneously
        "https://example.com/building3.jpg",
        "https://example.com/building4.jpg",
        "https://example.com/building5.jpg",
    ],
    output_images=[
        "s3://bucket/design1.png",  # All upload
        "s3://bucket/design2.png",  # simultaneously
        "s3://bucket/design3.png",
    ]
)
```

**Performance gains:**
- Loading 5 images: 5x faster (from 7.5s to 1.5s)
- Saving 3 images: 3x faster (from 3s to 1s)
- Overall speedup scales linearly with number of images

### Aspect Ratio Control

Use appropriate aspect ratios to reduce generation time and cost:

```python
# Different aspect ratios
result = await generator.generate(
    prompt="A wide landscape",
    output_images=["output.png"],
    aspect_ratio="16:9"  # or (16, 9)
)
```

Available ratios: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, or custom tuples.

## Advanced CLI Usage

### Piping and Shell Integration

```bash
# Pipe prompt from file
cat prompt.txt | imagen generate -o output.png

# Pipe prompt from command
echo "a sunset over mountains" | imagen generate -o sunset.png

# Use in loops
for prompt in "cat" "dog" "bird"; do
  imagen generate "$prompt" -o "${prompt}.png"
done

# Chain with other tools
cat prompts.txt | while read prompt; do
  imagen generate "$prompt" -o "$(echo $prompt | tr ' ' '_').png"
done
```

### JSON Output for Scripting

```bash
# Generate with JSON output
result=$(imagen generate "a landscape" -o output.png --json)
echo "$result" | jq '.image_path'
echo "$result" | jq '.s3_uri'
echo "$result" | jq '.http_url'

# Analyze with JSON output
description=$(imagen analyze image.jpg --json)
echo "$description" | jq '.description'
echo "$description" | jq '.model'
```

### Configuration Management

```bash
# View all configuration
imagen config list

# View as JSON
imagen config list --json

# Get specific value
model=$(imagen config get default_model)

# Show config file location
imagen config path

# Set multiple values
imagen config set default_model gemini-2.0-flash-exp
imagen config set temperature 0.8
imagen config set aspect_ratio 16:9
```

### Multiple Output Images with Labels

```python
result = await generator.generate(
    prompt="Create 3 variations of a mountain landscape",
    output_images=[
        ("Sunrise version", "mountain_sunrise.png"),
        ("Sunset version", "mountain_sunset.png"),
        ("Night version", "mountain_night.png")
    ]
)

# Access labeled outputs
for label, uri in zip(result.image_labels, result.image_locations):
    print(f"{label}: {uri}")
```

### Labeled Input Images

```python
result = await generator.generate(
    prompt="Blend the artistic style from Photo A with the composition from Photo B",
    input_images=[
        ("Photo A (style):", "style_reference.jpg"),
        ("Photo B (composition):", "composition_reference.jpg")
    ],
    output_images=["blended_result.png"]
)
```

### Environment Variables

All configuration can be set via environment variables:

```bash
# Set API key
export GOOGLE_API_KEY=your_key

# Set AWS credentials
export GV_AWS_ACCESS_KEY_ID=your_key
export GV_AWS_SECRET_ACCESS_KEY=your_secret
export GV_AWS_STORAGE_BUCKET_NAME=your_bucket

# Set LangSmith
export LANGSMITH_API_KEY=your_key
export LANGSMITH_PROJECT=your_project
export LANGSMITH_TRACING=true

# Run command (uses env vars)
imagen generate "a cat" -o cat.png
```

## Best Practices

1. **Use configuration file** for credentials instead of passing them as arguments
2. **Use `--json` flag** when scripting for easier parsing
3. **Enable LangSmith tracing** for debugging and monitoring in production
4. **Use labeled inputs** when working with multiple reference images
5. **Store generated images in S3** for easier sharing and persistence
6. **Set appropriate temperature** (0.0 for consistency, 0.8-1.0 for creativity)
7. **Use specific prompts** for better results
8. **Test with different models** to find the best one for your use case
9. **Leverage parallelization** by loading/saving multiple images at once
10. **Configure safety settings** appropriately for your use case

## Troubleshooting

### API Key Not Found

```
Error: Google API key not configured.
```

**Solution:**
```bash
imagen keys set google YOUR_KEY
# or
export GOOGLE_API_KEY=YOUR_KEY
```

### Rate Limit Exceeded

```
Error: quota or rate limit exceeded
```

**Solution:** Wait a moment and try again. Free tier limits: 10 requests/minute, 1500/day.

### S3 Access Denied

```
Error: bucket or s3 access denied
```

**Solution:**
```bash
imagen keys set aws-access-key YOUR_KEY
imagen keys set aws-secret-key YOUR_SECRET
imagen config set aws_storage_bucket_name YOUR_BUCKET
```

### File Not Found

```
Error: Input file does not exist: image.jpg
```

**Solution:** Check the file path is correct. For S3 URIs, use `s3://bucket/key` format.

### Safety Blocked

```
ValueError: No content parts in response. Finish reason: IMAGE_SAFETY
```

**Solution:** Adjust your prompt or use more relaxed safety settings (see [Safety Settings](#safety-settings)).

## Examples Directory

See the [`examples/`](examples/) directory for complete working examples:

- [`basic_generation.py`](examples/basic_generation.py) - Simple text-to-image
- [`image_analysis.py`](examples/image_analysis.py) - Analyze images
- [`labeled_inputs.py`](examples/labeled_inputs.py) - Use labeled images
- [`s3_integration.py`](examples/s3_integration.py) - S3 upload/download
- [`langsmith_tracing.py`](examples/langsmith_tracing.py) - Enable tracing

## Additional Resources

- [README.md](README.md) - Main documentation and quick start
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development and contribution guidelines
- [docs/SAFETY_FILTERING.md](docs/SAFETY_FILTERING.md) - Safety filtering details
- [GitHub Issues](https://github.com/aviadr1/gemini-imagen/issues) - Report bugs or request features
