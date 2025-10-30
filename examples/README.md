# Examples

This directory contains example scripts demonstrating various features of gemini-imagen.

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Add your API keys to `.env`:
   - `GOOGLE_API_KEY` is required for all examples
   - AWS credentials are only needed for S3 examples
   - LangSmith API key is only needed for tracing examples

3. Install the package:
   ```bash
   pip install gemini-imagen
   ```

## Examples

### Basic Usage

- **`basic_generation.py`** - Simple text-to-image generation
  ```bash
  python basic_generation.py
  ```

- **`image_analysis.py`** - Analyze an image and get text description
  ```bash
  python image_analysis.py
  ```

### Advanced Features

- **`labeled_inputs.py`** - Use labeled images in prompts for better control
  ```bash
  python labeled_inputs.py
  ```

- **`s3_integration.py`** - Upload/download images to/from S3
  ```bash
  python s3_integration.py
  ```
  *Requires AWS credentials*

- **`langsmith_tracing.py`** - Enable LangSmith tracing for observability
  ```bash
  python langsmith_tracing.py
  ```
  *Requires LangSmith API key*

## Running Examples

All examples should be run from this directory:

```bash
cd examples
python basic_generation.py
```
