# gemini-imagen

[![PyPI version](https://badge.fury.io/py/gemini-imagen.svg)](https://badge.fury.io/py/gemini-imagen)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/aviadr1/gemini-imagen/actions/workflows/ci.yml/badge.svg)](https://github.com/aviadr1/gemini-imagen/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/aviadr1/gemini-imagen/branch/main/graph/badge.svg)](https://codecov.io/gh/aviadr1/gemini-imagen)

A powerful command-line tool for Google Gemini's image generation and analysis capabilities.

> **📚 For Python library usage**, see [LIBRARY.md](LIBRARY.md)
> **🚀 For advanced features**, see [ADVANCED_USAGE.md](ADVANCED_USAGE.md)
> **🤝 For contributing**, see [CONTRIBUTING.md](CONTRIBUTING.md)

## Features

- 🎨 **Text-to-Image Generation** - Create images from text prompts
- 📐 **Aspect Ratio Control** - Custom aspect ratios (16:9, 1:1, 9:16, etc.)
- 🏷️ **Labeled Input Images** - Reference images by name in prompts
- 💬 **Image Analysis** - Get detailed text descriptions of images
- ✏️ **Image Editing** - Edit images using reference images and prompts
- ☁️ **S3 Integration** - Seamless AWS S3 upload/download
- 📈 **LangSmith Tracing** - Full observability for debugging
- 🔒 **Safety Settings** - Configurable content filtering
- 🔄 **Self-Updating** - Built-in update system for standalone installs

## Installation

### Quick Install (Recommended)

Install `imagen` CLI without manually managing Python or dependencies:

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.ps1 | iex
```

The installer will:
- Create an isolated environment for gemini-imagen
- Install all dependencies automatically
- Add `imagen` command to your PATH
- Support self-updates with `imagen self-update`

> **Note:** Python 3.12+ is required but the installer handles everything automatically.

### Traditional Installation (with pip)

**Basic Installation:**
```bash
pip install gemini-imagen
```

**With S3 Support:**
```bash
pip install gemini-imagen[s3]
```

**From Source:**
```bash
git clone https://github.com/aviadr1/gemini-imagen.git
cd gemini-imagen
pip install -e ".[dev,s3]"
```

For detailed installation instructions, see [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Quick Start

### 1. Set Up API Key

```bash
# Option 1: Save in config (recommended)
imagen keys set google YOUR_API_KEY

# Option 2: Environment variable
export GOOGLE_API_KEY="your-api-key-here"
```

Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

### 2. Generate Your First Image

```bash
imagen generate "a serene Japanese garden with cherry blossoms" -o garden.png
```

### 3. Analyze an Image

```bash
imagen analyze photo.jpg
```

### 4. Edit an Image

```bash
imagen edit "make it sunset" -i original.jpg -o edited.png
```

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `generate` | Generate images from text prompts | `imagen generate "a cat" -o cat.png` |
| `analyze` | Analyze and describe images | `imagen analyze image.jpg` |
| `edit` | Edit images using reference images | `imagen edit "make it brighter" -i photo.jpg -o out.png` |
| `upload` | Upload images to S3 | `imagen upload local.png s3://bucket/remote.png` |
| `download` | Download images from S3 | `imagen download s3://bucket/image.png local.png` |
| `keys` | Manage API keys | `imagen keys set google YOUR_KEY` |
| `config` | Manage configuration | `imagen config set default_model gemini-2.0-flash-exp` |
| `models` | List and manage models | `imagen models list` |
| `template` | Manage generation templates | `imagen template save my-template` |
| `langsmith` | LangSmith tracing tools | `imagen langsmith replay TRACE_URL` |
| `self-update` | Update to latest version | `imagen self-update` |

## Common Usage Patterns

### Generate with Options

```bash
# Control generation parameters
imagen generate "futuristic cityscape" -o city.png \
  --temperature 0.8 \
  --aspect-ratio 16:9 \
  --safety-setting preset:relaxed

# With verbose output for debugging
imagen -v generate "test prompt" -o test.png
```

### Use Input Images

```bash
# Single input image
imagen generate "make this image more vibrant" \
  -i photo.jpg \
  -o vibrant.png

# Multiple labeled inputs
imagen generate "blend these two art styles" \
  -i style1.jpg --label "Impressionist style:" \
  -i style2.jpg --label "Cubist style:" \
  -o blended.png
```

### Pipe Input from Commands

```bash
# From echo
echo "a sunset over mountains" | imagen generate -o sunset.png

# From file
cat prompt.txt | imagen generate -o output.png

# From other commands
fortune | imagen generate -o fortune.png
```

### Work with S3

```bash
# Generate directly to S3
imagen generate "a robot" -o s3://my-bucket/robot.png

# Use S3 input images
imagen edit "make it brighter" \
  -i s3://my-bucket/input.png \
  -o s3://my-bucket/output.png

# Upload existing images
imagen upload local.png s3://my-bucket/remote.png

# Download from S3
imagen download s3://my-bucket/image.png local.png
```

### Templates for Repeated Generation

```bash
# Save current parameters as a template
imagen generate "test prompt" \
  --temperature 0.8 \
  --aspect-ratio 16:9 \
  --template save my-style

# Use template with different prompt
imagen generate "new prompt" --template my-style -o new.png

# List templates
imagen template list
```

### JSON Output

```bash
# Get structured output
imagen generate "a cat" -o cat.png --json

# Output:
# {
#   "image_location": "cat.png",
#   "model": "gemini-2.5-flash-image",
#   "safety_ratings": {...},
#   "finish_reason": "STOP"
# }

# Analyze with JSON output
imagen analyze image.jpg --json
```

## Configuration

### Set Default Values

```bash
# Set defaults for common options
imagen config set default_model gemini-2.0-flash-exp
imagen config set temperature 0.8
imagen config set aspect_ratio 16:9
imagen config set safety_settings relaxed

# View all configuration
imagen config list

# Get specific value
imagen config get temperature

# Show config file location
imagen config path  # ~/.config/imagen/config.yaml
```

### Configuration Precedence

Values are resolved in order (highest to lowest priority):
1. **Command-line flags** - `--temperature 0.9`
2. **Environment variables** - `TEMPERATURE=0.8`
3. **Config file** - `~/.config/imagen/config.yaml`
4. **Default values** - Built-in defaults

### Environment Variables

```bash
# Required
export GOOGLE_API_KEY=your_google_api_key

# Optional - for S3 features
export GV_AWS_ACCESS_KEY_ID=your_aws_access_key
export GV_AWS_SECRET_ACCESS_KEY=your_aws_secret_key
export GV_AWS_STORAGE_BUCKET_NAME=your-bucket-name

# Optional - for LangSmith tracing
export LANGSMITH_API_KEY=your_langsmith_api_key
export LANGSMITH_TRACING=true
export LANGSMITH_PROJECT=your-project-name
```

### Safety Settings

Control content filtering with presets or custom settings:

```bash
# Use preset
imagen generate "prompt" -o out.png --safety-setting preset:relaxed

# Available presets:
# - strict: Maximum filtering
# - default: Balanced filtering
# - relaxed: Minimal filtering
# - none: No filtering

# Custom per-category settings
imagen generate "prompt" -o out.png \
  --safety-setting SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH \
  --safety-setting DANGEROUS_CONTENT:BLOCK_MEDIUM_AND_ABOVE
```

See [docs/SAFETY_FILTERING.md](docs/SAFETY_FILTERING.md) for detailed safety configuration.

## Advanced Features

### LangSmith Tracing

Enable observability for debugging and monitoring:

```bash
# Enable tracing for a command
imagen generate "test" -o test.png --trace

# Add tags for organization
imagen generate "test" -o test.png \
  --trace \
  --tag experiment \
  --tag version:1.0

# Replay from LangSmith trace
imagen langsmith replay https://smith.langchain.com/public/...
```

### Template System

Create reusable generation workflows:

```bash
# Save current settings as template
imagen generate "example" -o test.png \
  --temperature 0.8 \
  --aspect-ratio 16:9 \
  --template save my-template

# Use template with overrides
imagen generate "new prompt" \
  --template my-template \
  --temperature 0.9 \
  -o new.png

# Save template from job file
imagen template save my-template job.json

# List all templates
imagen template list

# Show template content
imagen template show my-template
```

### Batch Processing

```bash
# Generate multiple images from file
cat prompts.txt | while read prompt; do
  imagen generate "$prompt" -o "output_$(date +%s).png"
done

# Process directory of images
for img in *.jpg; do
  imagen analyze "$img" > "${img%.jpg}.txt"
done
```

## Updating

### Standalone Installation

```bash
# Check for updates
imagen self-update --check

# Update to latest version
imagen self-update

# Update to specific version
imagen self-update --version 0.6.0
```

### Pip Installation

```bash
pip install --upgrade gemini-imagen
```

## Troubleshooting

### Common Issues

**API Key Errors:**
```bash
# Verify key is set
imagen keys list

# Set key if missing
imagen keys set google YOUR_KEY
```

**Import Errors (pip installation):**
```bash
# Reinstall with dependencies
pip install --force-reinstall gemini-imagen[s3]
```

**S3 Upload Failures:**
```bash
# Verify AWS credentials
imagen keys list

# Set AWS credentials
imagen keys set aws-access-key YOUR_KEY
imagen keys set aws-secret-key YOUR_SECRET
imagen config set aws_storage_bucket_name YOUR_BUCKET
```

### Verbose Output

Use `-v` or `--verbose` flag for detailed error information:

```bash
imagen -v generate "test" -o test.png
```

### Get Help

```bash
# General help
imagen --help

# Command-specific help
imagen generate --help
imagen analyze --help

# Show version
imagen --version
```

## Documentation

- **[LIBRARY.md](LIBRARY.md)** - Python library API documentation and examples
- **[ADVANCED_USAGE.md](ADVANCED_USAGE.md)** - Advanced features, automation, integration
- **[docs/SAFETY_FILTERING.md](docs/SAFETY_FILTERING.md)** - Safety configuration details
- **[docs/INSTALLATION.md](docs/INSTALLATION.md)** - Detailed installation guide
- **[RELEASING.md](RELEASING.md)** - Release process for maintainers
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development setup and contributing

## Examples

See the [`examples/`](examples/) directory for complete working examples:

- CLI usage examples in shell scripts
- Python library integration examples
- Advanced automation workflows
- Web framework integration

## Pricing

### Image Generation (gemini-2.5-flash-image)
- **Cost**: $30/1M output tokens
- **Per Image**: ~$0.039 (1290 tokens at 1024x1024)

### Text Model (gemini-2.5-flash)
- **Input**: $0.30/1M tokens
- **Output**: $1.20/1M tokens

## Limitations

- **Multiple images**: Gemini may not always generate the exact number requested
- **Rate limits** (free tier): 10 requests/minute, 1500/day
- **Aspect ratios**: Limited to supported ratios (1:1, 16:9, 9:16, 4:3, 3:4)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development environment setup
- Code style guidelines
- Testing requirements
- Pull request process

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built on [`google-genai`](https://github.com/googleapis/python-genai) - Google's unified GenAI SDK
- Uses [`langsmith`](https://github.com/langchain-ai/langsmith-sdk) for tracing
- S3 integration via [`boto3`](https://github.com/boto/boto3)
- Type validation with [`pydantic`](https://github.com/pydantic/pydantic) v2
- CLI framework with [`click`](https://github.com/pallets/click)

## Support

- **Issues**: [GitHub Issues](https://github.com/aviadr1/gemini-imagen/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aviadr1/gemini-imagen/discussions)
- **Documentation**: This README and linked documentation files
- **Examples**: [`examples/`](examples/) directory

---

Made with ❤️ by [Aviad Rozenhek](https://github.com/aviadr1)
