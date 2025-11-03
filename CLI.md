# Imagen CLI Documentation

A command-line interface for generating and analyzing images using Google Gemini.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Commands](#commands)
  - [generate](#generate) - Generate images from text prompts
  - [analyze](#analyze) - Analyze and describe images
  - [edit](#edit) - Edit images using reference images
  - [upload](#upload) - Upload images to S3
  - [download](#download) - Download images from S3
  - [keys](#keys) - Manage API keys
  - [config](#config) - Manage configuration
  - [models](#models) - List and manage models
- [Advanced Usage](#advanced-usage)
- [Examples](#examples)

## Installation

Install the package with the CLI:

```bash
# Using uv (recommended)
uv pip install gemini-imagen

# Using pip
pip install gemini-imagen
```

After installation, the `imagen` command will be available in your terminal.

## Quick Start

1. **Set up your API key:**

```bash
imagen keys set google YOUR_GOOGLE_API_KEY
```

2. **Generate an image:**

```bash
imagen generate "a serene mountain landscape at sunset" -o landscape.png
```

3. **Analyze an image:**

```bash
imagen analyze photo.jpg
```

That's it! You're ready to use the CLI.

## Configuration

### Configuration File

The CLI stores configuration in `~/.config/imagen/config.yaml` (or `$XDG_CONFIG_HOME/imagen/config.yaml`).

### Configuration Precedence

Configuration values are resolved in the following order (highest to lowest priority):

1. **Command-line flags** (e.g., `--model gemini-2.0-flash`)
2. **Environment variables** (e.g., `GOOGLE_API_KEY`)
3. **Config file** (`~/.config/imagen/config.yaml`)
4. **Default values**

### Required Configuration

- **Google API Key**: Required for all operations
  ```bash
  imagen keys set google YOUR_KEY
  # or set environment variable
  export GOOGLE_API_KEY=YOUR_KEY
  ```

### Optional Configuration

- **AWS Credentials** (for S3 support):
  ```bash
  imagen keys set aws-access-key YOUR_ACCESS_KEY
  imagen keys set aws-secret-key YOUR_SECRET_KEY
  imagen config set aws_storage_bucket_name YOUR_BUCKET
  ```

- **LangSmith** (for tracing):
  ```bash
  imagen config set langsmith_api_key YOUR_KEY
  imagen config set langsmith_project YOUR_PROJECT
  imagen config set langsmith_tracing true
  ```

- **Default Model**:
  ```bash
  imagen config set default_model gemini-2.0-flash-exp
  ```

## Commands

### generate

Generate images from text prompts.

**Syntax:**
```bash
imagen generate [PROMPT] -o OUTPUT [OPTIONS]
```

**Arguments:**
- `PROMPT` - Text description of the image to generate (can be piped via stdin)

**Required Options:**
- `-o, --output PATH` - Output file path or S3 URI

**Options:**
- `-i, --input PATH` - Input image(s) for reference (can be specified multiple times)
- `--label TEXT` - Label for input image (paired with -i in same order)
- `-m, --model NAME` - Model to use (default: from config or gemini-2.0-flash-exp)
- `--temperature FLOAT` - Sampling temperature (0.0-1.0, higher = more creative)
- `--text` - Also request text output explaining the generation
- `--aspect-ratio RATIO` - Aspect ratio (e.g., '16:9', '1:1', '9:16')
- `--trace/--no-trace` - Enable LangSmith tracing (default: from config)
- `--tag TEXT` - Tag for LangSmith tracing (can be specified multiple times)
- `--json` - Output result as JSON

**Examples:**

```bash
# Basic generation
imagen generate "a serene landscape" -o output.png

# With temperature control
imagen generate "a robot" -o robot.png --temperature 0.8

# Using input images for reference
imagen generate "blend these styles" -i ref1.jpg -i ref2.jpg -o result.png

# With labeled inputs
imagen generate "combine styles" -i style.jpg --label "Style:" -i comp.jpg --label "Composition:" -o out.png

# Piped input
echo "a cat" | imagen generate -o cat.png
cat prompt.txt | imagen generate -o image.png

# Save to S3
imagen generate "a sunset" -o s3://my-bucket/sunset.png

# Get JSON output
imagen generate "a mountain" -o mountain.png --json

# With aspect ratio
imagen generate "landscape" -o wide.png --aspect-ratio 16:9

# With text explanation
imagen generate "futuristic city" -o city.png --text
```

---

### analyze

Analyze and describe images.

**Syntax:**
```bash
imagen analyze IMAGE_PATH [OPTIONS]
```

**Arguments:**
- `IMAGE_PATH` - Path to image (local file, S3 URI, or HTTP URL)

**Options:**
- `-p, --prompt TEXT` - Custom analysis prompt (default: "Describe this image in detail")
- `-m, --model NAME` - Model to use (default: from config)
- `--trace/--no-trace` - Enable LangSmith tracing
- `--tag TEXT` - Tag for LangSmith tracing
- `--json` - Output result as JSON

**Examples:**

```bash
# Basic analysis
imagen analyze image.jpg

# Custom prompt
imagen analyze photo.png -p "What colors are in this image?"

# Analyze S3 image
imagen analyze s3://my-bucket/image.png

# Analyze HTTP URL
imagen analyze https://example.com/image.jpg

# Get JSON output
imagen analyze image.jpg --json

# With custom model
imagen analyze image.jpg -m gemini-2.0-flash
```

---

### edit

Edit images using reference images and prompts.

**Syntax:**
```bash
imagen edit [PROMPT] -i INPUT [INPUT ...] -o OUTPUT [OPTIONS]
```

**Arguments:**
- `PROMPT` - Description of desired changes (can be piped via stdin)

**Required Options:**
- `-i, --input PATH` - Input image(s) (required, can be specified multiple times)
- `-o, --output PATH` - Output file path or S3 URI

**Options:**
- `--label TEXT` - Label for input image (paired with -i in same order)
- `-m, --model NAME` - Model to use
- `--temperature FLOAT` - Sampling temperature (0.0-1.0)
- `--aspect-ratio RATIO` - Aspect ratio
- `--trace/--no-trace` - Enable LangSmith tracing
- `--tag TEXT` - Tag for LangSmith tracing
- `--json` - Output result as JSON

**Examples:**

```bash
# Edit with single reference
imagen edit "make it sunset" -i original.jpg -o edited.png

# Blend multiple styles
imagen edit "blend these styles" -i style1.jpg -i style2.jpg -o result.png

# With labeled inputs
imagen edit "combine" -i photo.jpg --label "Photo:" -i art.jpg --label "Art style:" -o out.png

# Piped prompt
echo "add mountains in background" | imagen edit -i photo.jpg -o edited.png

# Save to S3
imagen edit "enhance" -i image.jpg -o s3://my-bucket/enhanced.png

# Get JSON output
imagen edit "make warmer" -i photo.jpg -o warm.png --json
```

---

### upload

Upload an image to S3.

**Syntax:**
```bash
imagen upload SOURCE DESTINATION [OPTIONS]
```

**Arguments:**
- `SOURCE` - Local file path
- `DESTINATION` - S3 URI (s3://bucket/key)

**Options:**
- `--json` - Output result as JSON

**Examples:**

```bash
# Upload to S3
imagen upload local.png s3://my-bucket/remote.png

# Upload with JSON output
imagen upload image.jpg s3://bucket/image.jpg --json
```

**Requirements:**
- AWS credentials must be configured
- Use `imagen keys set aws-access-key` and `imagen keys set aws-secret-key`
- Or set `GV_AWS_ACCESS_KEY_ID` and `GV_AWS_SECRET_ACCESS_KEY` environment variables

---

### download

Download an image from S3.

**Syntax:**
```bash
imagen download SOURCE DESTINATION [OPTIONS]
```

**Arguments:**
- `SOURCE` - S3 URI (s3://bucket/key)
- `DESTINATION` - Local file path

**Options:**
- `--json` - Output result as JSON

**Examples:**

```bash
# Download from S3
imagen download s3://my-bucket/remote.png local.png

# Download with JSON output
imagen download s3://bucket/image.jpg image.jpg --json
```

**Requirements:**
- AWS credentials must be configured

---

### keys

Manage API keys and credentials.

**Subcommands:**

#### keys set

Set an API key or credential.

**Syntax:**
```bash
imagen keys set KEY_NAME VALUE
```

**Key Names:**
- `google` - Google Gemini API key
- `aws-access-key` - AWS Access Key ID
- `aws-secret-key` - AWS Secret Access Key

**Examples:**

```bash
imagen keys set google YOUR_GOOGLE_API_KEY
imagen keys set aws-access-key YOUR_AWS_ACCESS_KEY
imagen keys set aws-secret-key YOUR_AWS_SECRET_KEY
```

#### keys list

List all configured keys (values are masked).

**Syntax:**
```bash
imagen keys list
```

#### keys delete

Delete an API key or credential.

**Syntax:**
```bash
imagen keys delete KEY_NAME
```

**Examples:**

```bash
imagen keys delete google
```

---

### config

View and modify configuration.

**Subcommands:**

#### config set

Set a configuration value.

**Syntax:**
```bash
imagen config set KEY VALUE
```

**Common Keys:**
- `google_api_key` - Google Gemini API key
- `aws_access_key_id` - AWS Access Key ID
- `aws_secret_access_key` - AWS Secret Access Key
- `aws_storage_bucket_name` - Default S3 bucket
- `langsmith_api_key` - LangSmith API key
- `langsmith_project` - LangSmith project name
- `langsmith_tracing` - Enable LangSmith tracing (true/false)
- `default_model` - Default model to use

**Examples:**

```bash
imagen config set default_model gemini-2.0-flash-exp
imagen config set langsmith_tracing true
imagen config set aws_storage_bucket_name my-bucket
```

#### config get

Get a configuration value.

**Syntax:**
```bash
imagen config get KEY
```

**Examples:**

```bash
imagen config get default_model
```

#### config list

List all configuration values.

**Syntax:**
```bash
imagen config list
imagen config list --json
```

#### config delete

Delete a configuration value.

**Syntax:**
```bash
imagen config delete KEY
```

#### config path

Show the path to the configuration file.

**Syntax:**
```bash
imagen config path
```

---

### models

List and manage models.

**Subcommands:**

#### models list

List available models.

**Syntax:**
```bash
imagen models list
```

#### models default

Get or set the default model.

**Syntax:**
```bash
imagen models default              # Show current default
imagen models default MODEL_NAME   # Set new default
```

**Examples:**

```bash
# Show current default
imagen models default

# Set new default
imagen models default gemini-2.0-flash-exp
```

---

## Advanced Usage

### Piping and Shell Integration

The CLI is designed to work well with Unix pipes and shell scripting:

```bash
# Pipe prompt from file
cat prompt.txt | imagen generate -o output.png

# Pipe prompt from command
echo "a sunset over mountains" | imagen generate -o sunset.png

# Use in scripts
for prompt in "cat" "dog" "bird"; do
  imagen generate "$prompt" -o "${prompt}.png"
done

# Chain with other tools
cat prompts.txt | while read prompt; do
  imagen generate "$prompt" -o "$(echo $prompt | tr ' ' '_').png"
done
```

### JSON Output

Use `--json` for machine-readable output:

```bash
# Generate with JSON output
resultado=$(imagen generate "a landscape" -o output.png --json)
echo "$resultado" | jq '.image_path'

# Analyze with JSON output
description=$(imagen analyze image.jpg --json)
echo "$description" | jq '.description'
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

### S3 Integration

Work seamlessly with S3 storage:

```bash
# Input from S3, output to S3
imagen generate "enhance this" -i s3://bucket/input.jpg -o s3://bucket/output.jpg

# Download from S3, process, upload back
imagen download s3://bucket/original.png local.png
imagen edit "make it brighter" -i local.png -o edited.png
imagen upload edited.png s3://bucket/edited.png
```

### LangSmith Tracing

Enable tracing for monitoring and debugging:

```bash
# Enable tracing for a single command
imagen generate "a robot" -o robot.png --trace --tag experiment --tag v1

# Enable globally
imagen config set langsmith_tracing true
imagen config set langsmith_project my-project

# All subsequent commands will be traced
imagen generate "a cat" -o cat.png
```

## Examples

### Example 1: Generate Multiple Variations

```bash
# Generate 3 images with different prompts
for i in {1..3}; do
  imagen generate "abstract art style $i" -o "art_$i.png" --temperature 0.9
done
```

### Example 2: Batch Image Analysis

```bash
# Analyze all images in a directory
for img in *.jpg; do
  echo "Analyzing $img..."
  imagen analyze "$img" > "${img%.jpg}_description.txt"
done
```

### Example 3: Style Transfer Pipeline

```bash
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

### Example 4: Automated Image Generation Workflow

```bash
#!/bin/bash
# generate_images.sh

# Read prompts from file
while IFS= read -r prompt; do
  # Generate filename from prompt
  filename=$(echo "$prompt" | tr ' ' '_' | tr '[:upper:]' '[:lower:]').png

  # Generate image
  echo "Generating: $filename"
  imagen generate "$prompt" -o "$filename" --json | jq '.image_path'

  # Upload to S3
  imagen upload "$filename" "s3://my-bucket/generated/$filename"
done < prompts.txt
```

### Example 5: Quality Control with Analysis

```bash
#!/bin/bash
# generate_and_verify.sh

# Generate image
imagen generate "$1" -o output.png

# Analyze to verify it matches prompt
description=$(imagen analyze output.png -p "Does this image match: $1?" --json | jq -r '.description')

echo "Generated image"
echo "Verification: $description"
```

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

## Getting Help

- View command help: `imagen COMMAND --help`
- View general help: `imagen --help`
- Report issues: https://github.com/aviadr1/gemini-imagen/issues
- Documentation: https://github.com/aviadr1/gemini-imagen

## Best Practices

1. **Use configuration file** for credentials instead of passing them as arguments
2. **Use `--json` flag** when scripting for easier parsing
3. **Enable LangSmith tracing** for debugging and monitoring in production
4. **Use labeled inputs** when working with multiple reference images
5. **Store generated images in S3** for easier sharing and persistence
6. **Set appropriate temperature** (0.0 for consistency, 0.8-1.0 for creativity)
7. **Use specific prompts** for better results
8. **Test with different models** to find the best one for your use case
