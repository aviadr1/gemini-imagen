# Python Library Documentation

This guide covers using gemini-imagen as a Python library for integrating Google Gemini image generation into your applications.

> **For CLI usage**, see [README.md](README.md)
> **For advanced features**, see [ADVANCED_USAGE.md](ADVANCED_USAGE.md)
> **For contributing**, see [CONTRIBUTING.md](CONTRIBUTING.md)

## Table of Contents

- [Installation](#installation)
- [Quick Setup](#quick-setup)
- [Core Classes](#core-classes)
- [Basic Usage](#basic-usage)
- [Common Patterns](#common-patterns)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [API Reference](#api-reference)

## Installation

### Basic Installation

```bash
pip install gemini-imagen
```

### With S3 Support

```bash
pip install gemini-imagen[s3]
```

### For Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development setup instructions.

Quick setup for library development:

```bash
# Clone the repository
git clone https://github.com/aviadr1/gemini-imagen.git
cd gemini-imagen

# Install with development dependencies
pip install -e ".[dev,s3]"

# Or using uv (recommended)
uv sync --all-extras
```

## Quick Setup

### 1. Set API Key

```python
import os
os.environ["GOOGLE_API_KEY"] = "your-api-key-here"
```

Or use a `.env` file:

```env
GOOGLE_API_KEY=your-api-key-here
```

### 2. Import and Use

```python
from gemini_imagen import GeminiImageGenerator

# Create generator
generator = GeminiImageGenerator()

# Generate an image
result = await generator.generate(
    prompt="A serene Japanese garden with cherry blossoms",
    output_images=["garden.png"]
)

print(f"Image saved to: {result.image_location}")
```

## Core Classes

### GeminiImageGenerator

Main class for image generation and analysis.

```python
from gemini_imagen import GeminiImageGenerator

generator = GeminiImageGenerator(
    model_name="gemini-2.5-flash-image",  # Default image generation model
    api_key=None,                          # Auto-loads from GOOGLE_API_KEY env var
    log_images=True                        # Enable LangSmith logging
)
```

### GenerationResult

Result object returned by generate operations.

```python
from gemini_imagen import GenerationResult

# Access generated content
result.text                    # Generated text (if any)
result.images                  # List of PIL Image objects
result.image_locations         # List of saved file paths
result.image_s3_uris           # List of S3 URIs (if applicable)
result.image_http_urls         # List of HTTP URLs (if applicable)

# Convenience properties for first image
result.image                   # First PIL Image
result.image_location          # First file path
result.image_s3_uri            # First S3 URI
result.image_http_url          # First HTTP URL
```

### Safety Settings

```python
from gemini_imagen import SafetySetting, HarmCategory, HarmBlockThreshold

# Create safety settings
settings = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
    )
]
```

## Basic Usage

### Text-to-Image Generation

```python
import asyncio
from gemini_imagen import GeminiImageGenerator

async def generate_image():
    generator = GeminiImageGenerator()

    result = await generator.generate(
        prompt="A futuristic cityscape at sunset with flying cars",
        output_images=["cityscape.png"]
    )

    return result

# Run async code
result = asyncio.run(generate_image())
```

### Image Analysis

```python
async def analyze_image():
    generator = GeminiImageGenerator()

    result = await generator.generate(
        prompt="Describe this image in detail, including colors, objects, and mood",
        input_images=["photo.jpg"],
        output_text=True
    )

    print(result.text)
```

### Image Editing

```python
async def edit_image():
    generator = GeminiImageGenerator()

    result = await generator.generate(
        prompt="Make the sky more dramatic with sunset colors",
        input_images=["original.jpg"],
        output_images=["edited.jpg"]
    )
```

### Multiple Input Images

```python
async def blend_styles():
    generator = GeminiImageGenerator()

    result = await generator.generate(
        prompt="Combine the style of the first image with the composition of the second",
        input_images=[
            "style_reference.jpg",
            "composition_reference.jpg"
        ],
        output_images=["blended.png"]
    )
```

### Labeled Input Images

```python
async def labeled_inputs():
    generator = GeminiImageGenerator()

    result = await generator.generate(
        prompt="Blend the artistic style from Photo A with the composition from Photo B",
        input_images=[
            ("Photo A (style):", "style_reference.jpg"),
            ("Photo B (composition):", "composition_reference.jpg")
        ],
        output_images=["result.png"]
    )
```

## Common Patterns

### Using Context Manager

```python
from gemini_imagen import GeminiImageGenerator

async def generate_with_context():
    async with GeminiImageGenerator() as generator:
        result = await generator.generate(
            prompt="A mountain landscape",
            output_images=["mountain.png"]
        )
    return result
```

### Batch Processing

```python
async def batch_generate(prompts: list[str]):
    generator = GeminiImageGenerator()
    results = []

    for i, prompt in enumerate(prompts):
        result = await generator.generate(
            prompt=prompt,
            output_images=[f"output_{i}.png"]
        )
        results.append(result)

    return results

# Use with asyncio.gather for parallel processing
prompts = ["a cat", "a dog", "a bird"]
results = await asyncio.gather(*[
    generator.generate(prompt=p, output_images=[f"{p}.png"])
    for p in prompts
])
```

### With Safety Settings

```python
from gemini_imagen import GeminiImageGenerator, SafetySetting, HarmCategory, HarmBlockThreshold

async def generate_with_safety():
    generator = GeminiImageGenerator()

    # Relaxed settings for artistic content
    safety_settings = [
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
        )
    ]

    result = await generator.generate(
        prompt="A tasteful artistic nude statue",
        output_images=["statue.png"],
        safety_settings=safety_settings
    )
```

### With Temperature Control

```python
async def creative_generation():
    generator = GeminiImageGenerator()

    # Higher temperature for more creative/varied results
    result = await generator.generate(
        prompt="Abstract art with vibrant colors",
        output_images=["abstract.png"],
        temperature=0.9  # Range: 0.0 (deterministic) to 1.0 (creative)
    )
```

### With Aspect Ratio

```python
async def wide_landscape():
    generator = GeminiImageGenerator()

    result = await generator.generate(
        prompt="A panoramic mountain vista",
        output_images=["panorama.png"],
        aspect_ratio="16:9"  # or (16, 9) as tuple
    )
```

## Configuration

### Environment Variables

```python
import os

# Required
os.environ["GOOGLE_API_KEY"] = "your_google_api_key"

# Optional - for S3 features
os.environ["GV_AWS_ACCESS_KEY_ID"] = "your_aws_access_key"
os.environ["GV_AWS_SECRET_ACCESS_KEY"] = "your_aws_secret_key"
os.environ["GV_AWS_STORAGE_BUCKET_NAME"] = "your-bucket-name"

# Optional - for LangSmith tracing
os.environ["LANGSMITH_API_KEY"] = "your_langsmith_api_key"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "your-project-name"
```

### Programmatic Configuration

```python
from gemini_imagen import GeminiImageGenerator

generator = GeminiImageGenerator(
    model_name="gemini-2.5-flash-image",
    api_key="your-api-key",  # Override env var
    log_images=True           # Enable LangSmith
)
```

### S3 Configuration

See [ADVANCED_USAGE.md](ADVANCED_USAGE.md#s3-integration) for detailed S3 setup and usage.

```python
# Configure via environment variables
os.environ["GV_AWS_ACCESS_KEY_ID"] = "your_key"
os.environ["GV_AWS_SECRET_ACCESS_KEY"] = "your_secret"
os.environ["GV_AWS_STORAGE_BUCKET_NAME"] = "your_bucket"

# Use S3 URIs in your code
result = await generator.generate(
    prompt="A sunset",
    input_images=["s3://my-bucket/input.jpg"],
    output_images=["s3://my-bucket/output.png"]
)
```

### LangSmith Configuration

See [ADVANCED_USAGE.md](ADVANCED_USAGE.md#langsmith-tracing) for detailed LangSmith setup.

```python
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "your_key"
os.environ["LANGSMITH_PROJECT"] = "my-project"

generator = GeminiImageGenerator(log_images=True)

result = await generator.generate(
    prompt="A robot",
    output_images=["robot.png"],
    metadata={"user_id": "123"},
    tags=["production", "robot"]
)
```

## Error Handling

### Basic Error Handling

```python
from gemini_imagen import GeminiImageGenerator

async def generate_with_error_handling():
    generator = GeminiImageGenerator()

    try:
        result = await generator.generate(
            prompt="Your prompt",
            output_images=["output.png"]
        )
        return result
    except ValueError as e:
        # Handle API errors (e.g., safety blocking, invalid parameters)
        print(f"Generation failed: {e}")
    except FileNotFoundError as e:
        # Handle file errors
        print(f"File error: {e}")
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error: {e}")
```

### Safety Blocking

```python
async def handle_safety_blocking():
    generator = GeminiImageGenerator()

    try:
        result = await generator.generate(
            prompt="Your prompt",
            output_images=["output.png"]
        )
    except ValueError as e:
        error_msg = str(e)
        if "IMAGE_SAFETY" in error_msg:
            print("Content blocked for safety reasons")
            # Try with relaxed settings
            from gemini_imagen import SafetySetting, HarmCategory, HarmBlockThreshold

            result = await generator.generate(
                prompt="Your prompt",
                output_images=["output.png"],
                safety_settings=[
                    SafetySetting(
                        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
                    )
                ]
            )
```

See [docs/SAFETY_FILTERING.md](docs/SAFETY_FILTERING.md) for detailed safety filtering documentation.

## API Reference

### GeminiImageGenerator

#### Constructor

```python
GeminiImageGenerator(
    model_name: str = "gemini-2.5-flash-image",
    api_key: Optional[str] = None,
    log_images: bool = True
)
```

**Parameters:**
- `model_name` - Model to use for generation (default: "gemini-2.5-flash-image")
- `api_key` - Google API key (defaults to GOOGLE_API_KEY env var)
- `log_images` - Enable LangSmith logging (default: True)

#### generate() Method

```python
async def generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    input_images: Optional[List[ImageSource]] = None,
    temperature: Optional[float] = None,
    aspect_ratio: Optional[Union[str, Tuple[int, int]]] = None,
    safety_settings: Optional[List[SafetySetting]] = None,
    output_images: Optional[List[OutputImageSpec]] = None,
    output_text: bool = False,
    metadata: Optional[Dict[str, str]] = None,
    tags: Optional[List[str]] = None
) -> GenerationResult
```

**Parameters:**
- `prompt` - Main prompt describing what to generate/analyze (required)
- `system_prompt` - System instructions for the model
- `input_images` - Input images (file paths, S3 URIs, PIL Images, or labeled tuples)
- `temperature` - Sampling temperature (0.0-1.0, higher = more creative)
- `aspect_ratio` - Output aspect ratio (e.g., "16:9", "1:1", or tuple like (16, 9))
- `safety_settings` - List of SafetySetting objects for content filtering
- `output_images` - Where to save generated images (file paths, S3 URIs, or labeled tuples)
- `output_text` - Whether to generate text output
- `metadata` - Metadata for LangSmith tracing
- `tags` - Tags for LangSmith tracing

**Returns:**
- `GenerationResult` - Object containing generated images, text, and metadata

**Type Definitions:**

```python
ImageSource = Union[
    Image.Image,           # PIL Image
    str,                   # File path or S3 URI
    Path,                  # Path object
    Tuple[str, Any]        # Labeled: ("Label:", image_source)
]

OutputImageSpec = Union[
    str,                   # File path or S3 URI
    Path,                  # Path object
    Tuple[str, Any]        # Labeled: ("Label:", output_location)
]
```

### GenerationResult

```python
@dataclass
class GenerationResult:
    text: Optional[str]                      # Generated text
    images: List[Image.Image]                # PIL Image objects
    image_labels: List[Optional[str]]        # Image labels
    image_locations: List[str]               # Local file paths
    image_s3_uris: List[Optional[str]]       # S3 URIs
    image_http_urls: List[Optional[str]]     # HTTP URLs

    # Convenience properties for first image
    @property
    def image(self) -> Optional[Image.Image]: ...

    @property
    def image_location(self) -> Optional[str]: ...

    @property
    def image_s3_uri(self) -> Optional[str]: ...

    @property
    def image_http_url(self) -> Optional[str]: ...
```

### SafetySetting

```python
from gemini_imagen import SafetySetting, HarmCategory, HarmBlockThreshold

setting = SafetySetting(
    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
)
```

**Available Categories:**
- `HARM_CATEGORY_SEXUALLY_EXPLICIT`
- `HARM_CATEGORY_DANGEROUS_CONTENT`
- `HARM_CATEGORY_HARASSMENT`
- `HARM_CATEGORY_HATE_SPEECH`

**Available Thresholds:**
- `BLOCK_NONE` - Disable blocking for this category
- `BLOCK_ONLY_HIGH` - Block only high-probability harmful content (relaxed)
- `BLOCK_MEDIUM_AND_ABOVE` - Block medium and high probability (default)
- `BLOCK_LOW_AND_ABOVE` - Block low, medium, and high probability (strict)

## Integration Examples

### Flask Web Application

```python
from flask import Flask, request, jsonify
from gemini_imagen import GeminiImageGenerator
import asyncio

app = Flask(__name__)
generator = GeminiImageGenerator()

@app.route('/generate', methods=['POST'])
def generate_image():
    data = request.json
    prompt = data.get('prompt')
    output_path = data.get('output_path', 'output.png')

    # Run async function in sync context
    result = asyncio.run(generator.generate(
        prompt=prompt,
        output_images=[output_path]
    ))

    return jsonify({
        'success': True,
        'image_path': result.image_location
    })
```

### FastAPI Application

```python
from fastapi import FastAPI
from gemini_imagen import GeminiImageGenerator

app = FastAPI()
generator = GeminiImageGenerator()

@app.post("/generate")
async def generate_image(prompt: str, output_path: str = "output.png"):
    result = await generator.generate(
        prompt=prompt,
        output_images=[output_path]
    )

    return {
        "success": True,
        "image_path": result.image_location
    }
```

### Background Task Processing

```python
from gemini_imagen import GeminiImageGenerator
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ImageGenerator:
    def __init__(self):
        self.generator = GeminiImageGenerator()
        self.executor = ThreadPoolExecutor(max_workers=4)

    def generate_sync(self, prompt: str, output_path: str):
        """Synchronous wrapper for async generate"""
        return asyncio.run(self.generator.generate(
            prompt=prompt,
            output_images=[output_path]
        ))

    def generate_background(self, prompt: str, output_path: str):
        """Submit generation to background thread pool"""
        future = self.executor.submit(
            self.generate_sync,
            prompt,
            output_path
        )
        return future
```

## Performance Tips

1. **Reuse Generator Instance**: Create one `GeminiImageGenerator` instance and reuse it
2. **Parallel Processing**: Use `asyncio.gather()` for multiple independent operations
3. **S3 for Large Scale**: Use S3 URIs for production deployments
4. **Enable LangSmith**: Monitor performance and debug issues in production
5. **Appropriate Aspect Ratios**: Use aspect ratios that match your use case

See [ADVANCED_USAGE.md](ADVANCED_USAGE.md#performance-optimization) for detailed performance optimization.

## Testing

### Unit Testing with Mocks

```python
from unittest.mock import AsyncMock, Mock, patch
from gemini_imagen import GeminiImageGenerator
import pytest

@pytest.mark.asyncio
async def test_generation():
    with patch.object(GeminiImageGenerator, 'generate', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = Mock(
            image_location="test.png",
            images=[Mock()]
        )

        generator = GeminiImageGenerator()
        result = await generator.generate(
            prompt="test",
            output_images=["test.png"]
        )

        assert result.image_location == "test.png"
```

### Integration Testing

See [CONTRIBUTING.md](CONTRIBUTING.md#running-tests) for running integration tests.

## Resources

- **CLI Documentation**: [README.md](README.md)
- **Advanced Features**: [ADVANCED_USAGE.md](ADVANCED_USAGE.md)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Safety Filtering**: [docs/SAFETY_FILTERING.md](docs/SAFETY_FILTERING.md)
- **Code Examples**: [examples/](examples/)
- **API Source**: [src/gemini_imagen/](src/gemini_imagen/)

## Support

- **Issues**: [GitHub Issues](https://github.com/aviadr1/gemini-imagen/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aviadr1/gemini-imagen/discussions)
- **Examples**: [examples/](examples/) directory

---

For CLI usage and installation instructions, see [README.md](README.md).
