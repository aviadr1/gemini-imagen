"""
Analyze command for gemini-imagen CLI.

Analyzes and describes images using Google Gemini.
"""

import asyncio
import sys

import click

from ...gemini_image_wrapper import GeminiImageGenerator
from ...models import GenerateParams
from ..config import get_config
from ..utils import (
    clear_progress,
    echo_error,
    format_api_error,
    output_json,
    show_progress,
    validate_input_path,
)


@click.command()
@click.argument("image_path", required=True)
@click.option(
    "-p",
    "--prompt",
    help="Custom analysis prompt (default: 'Describe this image in detail')",
)
@click.option(
    "-m",
    "--model",
    help="Model to use (default: from config or gemini-2.0-flash-exp)",
)
@click.option(
    "--trace/--no-trace",
    default=None,
    help="Enable LangSmith tracing (default: from config)",
)
@click.option(
    "--tag",
    "tags",
    multiple=True,
    help="Tag for LangSmith tracing (can be specified multiple times)",
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Output result as JSON",
)
def analyze(
    image_path: str,
    prompt: str | None,
    model: str | None,
    trace: bool | None,
    tags: tuple[str, ...],
    json_mode: bool,
) -> None:
    """
    Analyze and describe images.

    IMAGE_PATH can be a local file, S3 URI, or HTTP URL.

    \b
    Examples:
        # Basic analysis
        imagen analyze image.jpg

        # Custom prompt
        imagen analyze photo.png -p "What colors are in this image?"

        # Analyze S3 image
        imagen analyze s3://my-bucket/image.png

        # Get JSON output
        imagen analyze image.jpg --json

        # With custom model
        imagen analyze image.jpg -m gemini-2.0-flash

    \b
    Notes:
        - Supports local files, S3 URIs (s3://...), and HTTP URLs
        - Use -p to customize the analysis prompt
        - Default prompt: "Describe this image in detail"
    """
    try:
        # Validate input path
        image_path = validate_input_path(image_path)

        # Default prompt
        if prompt is None:
            prompt = "Describe this image in detail"

        # Get configuration
        cfg = get_config()

        # Get API key
        api_key = cfg.get_google_api_key()
        if not api_key:
            echo_error(
                "Google API key not configured.\n"
                "Set it with: imagen keys set google YOUR_KEY\n"
                "Or set GOOGLE_API_KEY environment variable.",
                json_mode=json_mode,
            )
            sys.exit(1)

        # Get model
        if model is None:
            model = cfg.get_analysis_model()

        # Get tracing setting
        if trace is None:
            trace = cfg.get_langsmith_tracing()

        # Show progress
        if not json_mode:
            show_progress("Analyzing image")

        # Create generator
        generator = GeminiImageGenerator(
            model_name=model,
            api_key=api_key,
            log_images=trace,
        )

        # Analyze - use Pydantic model for type safety and automatic None filtering
        params = GenerateParams(
            prompt=prompt,
            input_images=[image_path],
            output_text=True,
            tags=list(tags) if tags else None,
        )
        result = asyncio.run(generator.generate(params))

        # Clear progress
        if not json_mode:
            clear_progress()

        # Output results
        if json_mode:
            output_json(
                {
                    "success": True,
                    "description": result.text,
                    "model": model,
                    "image_path": image_path,
                }
            )
        else:
            if result.text:
                click.echo(result.text)
            else:
                echo_error("No description generated")
                sys.exit(1)

    except click.ClickException:
        raise
    except Exception as e:
        if not json_mode:
            clear_progress()
        error_msg = format_api_error(e)
        echo_error(error_msg, json_mode=json_mode)
        sys.exit(1)
