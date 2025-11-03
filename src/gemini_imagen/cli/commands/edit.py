"""
Edit command for gemini-imagen CLI.

Edits images using reference images and prompts.
"""

import asyncio
import sys

import click

from ...gemini_image_wrapper import GeminiImageGenerator
from ...models import GenerateParams, ImageSource
from ..config import get_config
from ..utils import (
    clear_progress,
    echo_error,
    echo_info,
    echo_success,
    format_api_error,
    get_prompt_from_args_or_stdin,
    output_json,
    show_progress,
    validate_input_path,
    validate_output_path,
)


@click.command()
@click.argument("prompt", required=False)
@click.option(
    "-i",
    "--input",
    "input_images",
    multiple=True,
    required=True,
    help="Input image(s) (required, can be specified multiple times)",
)
@click.option(
    "--label",
    "labels",
    multiple=True,
    help="Label for input image (paired with -i, same order)",
)
@click.option("-o", "--output", required=True, help="Output file path or S3 URI")
@click.option(
    "-m",
    "--model",
    help="Model to use (default: from config or gemini-2.0-flash-exp)",
)
@click.option(
    "--temperature",
    type=float,
    help="Sampling temperature (0.0-1.0, higher = more creative)",
)
@click.option(
    "--aspect-ratio",
    help="Aspect ratio (e.g., '16:9', '1:1', '9:16')",
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
def edit(
    prompt: str | None,
    input_images: tuple[str, ...],
    labels: tuple[str, ...],
    output: str,
    model: str | None,
    temperature: float | None,
    aspect_ratio: str | None,
    trace: bool | None,
    tags: tuple[str, ...],
    json_mode: bool,
) -> None:
    """
    Edit images using reference images and prompts.

    PROMPT can be provided as an argument or piped via stdin.
    At least one input image is required.

    \b
    Examples:
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

    \b
    Notes:
        - At least one input image is required (-i)
        - Input images can be local paths, S3 URIs, or HTTP URLs
        - Use --label to provide context for each input image
        - Labels help the model understand how to use each reference
    """
    try:
        # Check that we have input images
        if not input_images:
            echo_error(
                "At least one input image is required.\nUse -i IMAGE_PATH to specify input images.",
                json_mode=json_mode,
            )
            sys.exit(1)

        # Get prompt from args or stdin
        prompt_text = get_prompt_from_args_or_stdin(prompt)

        # Validate output path
        output = validate_output_path(output)

        # Validate input images
        validated_inputs: list[ImageSource] = []
        for i, input_path in enumerate(input_images):
            validated_path = validate_input_path(input_path)

            # Check if there's a corresponding label
            if i < len(labels):
                validated_inputs.append((labels[i], validated_path))
            else:
                validated_inputs.append(validated_path)

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
            model = cfg.get_generation_model()

        # Get tracing setting
        if trace is None:
            trace = cfg.get_langsmith_tracing()

        # Show progress
        if not json_mode:
            show_progress("Editing image")

        # Create generator
        generator = GeminiImageGenerator(
            model_name=model,
            api_key=api_key,
            log_images=trace,
        )

        # Build generation parameters using Pydantic model for type safety
        params = GenerateParams(
            prompt=prompt_text,
            input_images=validated_inputs,
            output_images=[output],
            temperature=temperature,
            aspect_ratio=aspect_ratio,
            tags=list(tags) if tags else None,
        )

        # Generate
        result = asyncio.run(generator.generate(params))

        # Clear progress
        if not json_mode:
            clear_progress()

        # Output results
        if json_mode:
            output_data = {
                "success": True,
                "image_path": result.image_location,
                "model": model,
            }

            if result.image_s3_uri:
                output_data["s3_uri"] = result.image_s3_uri

            if result.image_http_url:
                output_data["http_url"] = result.image_http_url

            output_json(output_data)
        else:
            echo_success(f"Edited image saved to: {result.image_location}")
            echo_info(f"Model: {model}")

            if result.image_s3_uri:
                echo_info(f"S3 URI: {result.image_s3_uri}")

            if result.image_http_url:
                echo_info(f"URL: {result.image_http_url}")

    except click.ClickException:
        raise
    except Exception as e:
        if not json_mode:
            clear_progress()
        error_msg = format_api_error(e)
        echo_error(error_msg, json_mode=json_mode)
        sys.exit(1)
