# gemini-imagen

[![PyPI version](https://badge.fury.io/py/gemini-imagen.svg)](https://badge.fury.io/py/gemini-imagen)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/aviadr1/gemini-imagen/actions/workflows/ci.yml/badge.svg)](https://github.com/aviadr1/gemini-imagen/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/aviadr1/gemini-imagen/branch/main/graph/badge.svg)](https://codecov.io/gh/aviadr1/gemini-imagen)

A comprehensive Python library and CLI for Google Gemini's image generation and analysis capabilities.

> **📚 For Python library usage**, see [LIBRARY.md](LIBRARY.md)
> **🚀 For advanced features**, see [ADVANCED_USAGE.md](ADVANCED_USAGE.md)
> **🤝 For contributing**, see [CONTRIBUTING.md](CONTRIBUTING.md)

## Features

- 🎨 **Text-to-Image Generation** - Create images from text prompts
- 📐 **Aspect Ratio Control** - Custom aspect ratios (16:9, 1:1, 9:16, etc.)
- 🏷️ **Labeled Input Images** - Reference images by name in prompts
- 📸 **Multiple Output Images** - Save same image to multiple locations
- 💬 **Image Analysis** - Get detailed text descriptions of images
- ☁️ **S3 Integration** - Seamless AWS S3 upload/download with URL logging
- 📈 **LangSmith Tracing** - Full observability for debugging and monitoring
- 🔒 **Safety Settings** - Configurable content filtering thresholds
- 🖥️ **CLI Tool** - Powerful command-line interface for all operations
- 🔄 **Type-Safe** - Full type hints with Pydantic validation

## Installation

### Quick Install (No Python Required)

Install `imagen` CLI without manually installing Python or managing dependencies:

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

> **Note:** Python 3.12+ is still required but the installer handles everything automatically.

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

### CLI Usage

```bash
# Set up your API key
export GOOGLE_API_KEY="your-api-key-here"

# Or save it in config
imagen keys set google YOUR_API_KEY

# Generate an image
imagen generate "a serene Japanese garden with cherry blossoms" -o garden.png

# Analyze an image
imagen analyze photo.jpg

# Edit an image
imagen edit "make it sunset" -i original.jpg -o edited.png

# Upload to S3
imagen upload local.png s3://my-bucket/remote.png
```

### Python Library

For detailed Python API documentation, see **[LIBRARY.md](LIBRARY.md)**.

Quick example:

```python
from gemini_imagen import GeminiImageGenerator

generator = GeminiImageGenerator()

# Generate an image
result = await generator.generate(
    prompt="A serene Japanese garden with cherry blossoms",
    output_images=["garden.png"]
)

print(f"Image saved to: {result.image_location}")
```

## CLI Commands

The CLI provides comprehensive image generation and management capabilities:

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
| `self-update` | Update to latest version | `imagen self-update` |

### Common CLI Options

```bash
# Generate with options
imagen generate "prompt" -o output.png \
  --temperature 0.8 \
  --aspect-ratio 16:9 \
  --safety-setting preset:relaxed \
  --trace \
  --json

# Use input images
imagen generate "blend these styles" \
  -i style.jpg --label "Style:" \
  -i composition.jpg --label "Composition:" \
  -o result.png

# Pipe input
echo "a sunset" | imagen generate -o sunset.png
cat prompt.txt | imagen generate -o output.png
```

## Python Library Examples

For comprehensive Python API documentation, examples, and integration patterns, see **[LIBRARY.md](LIBRARY.md)**.

Here are a few quick examples:

### Text-to-Image Generation

```python
result = await generator.generate(
    prompt="A futuristic cityscape at sunset with flying cars",
    output_images=["cityscape.png"],
    aspect_ratio="16:9",
    temperature=0.8
)
```

### Image Analysis

```python
result = await generator.generate(
    prompt="Describe this image in detail",
    input_images=["photo.jpg"],
    output_text=True
)
print(result.text)
```

### With Safety Settings

```python
from gemini_imagen import SafetySetting, HarmCategory, HarmBlockThreshold

result = await generator.generate(
    prompt="A tasteful artistic photo",
    output_images=["output.png"],
    safety_settings=[
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
        )
    ]
)
```

For more examples including S3 integration, LangSmith tracing, batch processing, and web framework integration, see **[LIBRARY.md](LIBRARY.md)**.

## Configuration

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

### CLI Configuration

```bash
# Set default values
imagen config set default_model gemini-2.0-flash-exp
imagen config set temperature 0.8
imagen config set aspect_ratio 16:9
imagen config set safety_settings relaxed

# View configuration
imagen config list

# Configuration location
imagen config path  # Shows: ~/.config/imagen/config.yaml
```

### Configuration Precedence

Values are resolved in order (highest to lowest priority):
1. Command-line flags
2. Environment variables
3. Config file (`~/.config/imagen/config.yaml`)
4. Default values

## Python API Reference

For complete API documentation with detailed examples, see **[LIBRARY.md](LIBRARY.md#api-reference)**.

Quick reference:

### GeminiImageGenerator

```python
generator = GeminiImageGenerator(
    model_name="gemini-2.5-flash-image",  # Image generation model (default)
    api_key=None,                         # Auto-loads from GOOGLE_API_KEY env var
    log_images=True                       # Enable LangSmith logging
)
```

### generate() Method

```python
result = await generator.generate(
    prompt: str,                           # Main prompt (required)
    system_prompt: Optional[str] = None,   # System instructions
    input_images: Optional[List] = None,   # Input images
    temperature: Optional[float] = None,   # Sampling temperature (0.0-1.0)
    aspect_ratio: Optional[str] = None,    # e.g., "16:9"
    safety_settings: Optional[List] = None,# Safety filtering
    output_images: Optional[List] = None,  # Generate images
    output_text: bool = False,             # Generate text
    metadata: Optional[Dict] = None,       # LangSmith metadata
    tags: Optional[List] = None            # LangSmith tags
) -> GenerationResult
```

See **[LIBRARY.md](LIBRARY.md)** for full type definitions, parameter details, and usage examples.

## Examples

See the [`examples/`](examples/) directory for complete working examples:

- [`basic_generation.py`](examples/basic_generation.py) - Simple text-to-image
- [`image_analysis.py`](examples/image_analysis.py) - Analyze images
- [`labeled_inputs.py`](examples/labeled_inputs.py) - Use labeled images
- [`s3_integration.py`](examples/s3_integration.py) - S3 upload/download
- [`langsmith_tracing.py`](examples/langsmith_tracing.py) - Enable tracing

## Documentation

- **[LIBRARY.md](LIBRARY.md)** - Python library documentation, API reference, integration examples
- **[ADVANCED_USAGE.md](ADVANCED_USAGE.md)** - Advanced features, S3, LangSmith, scripting, automation
- **[docs/SAFETY_FILTERING.md](docs/SAFETY_FILTERING.md)** - Safety filtering configuration and details
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development setup, testing, contributing guidelines

## Pricing

### Image Generation (gemini-2.5-flash-image)
- **Cost**: $30/1M output tokens
- **Per Image**: ~$0.039 (1290 tokens at 1024x1024)

### Text Model (gemini-2.5-flash)
- **Input**: $0.30/1M tokens
- **Output**: $1.20/1M tokens

## Limitations

- **Multiple images**: Gemini may not always generate the exact number requested
- **Structured output**: Only available with text model (separate call required)
- **Rate limits** (free tier): 10 requests/minute, 1500/day

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

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
- **Documentation**: This README and linked documentation files
- **Examples**: [`examples/`](examples/) directory

---

Made with ❤️ by [Aviad Rozenhek](https://github.com/aviadr1)
