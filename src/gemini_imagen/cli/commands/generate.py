"""
Generate command for gemini-imagen CLI.

Generates images from text prompts.
"""

import sys

import click

from ...gemini_image_wrapper import GeminiImageGenerator
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
@click.option("-o", "--output", required=True, help="Output file path or S3 URI")
@click.option(
    "-i",
    "--input",
    "input_images",
    multiple=True,
    help="Input image(s) for reference (can be specified multiple times)",
)
@click.option(
    "--label",
    "labels",
    multiple=True,
    help="Label for input image (paired with -i, same order)",
)
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
    "--text",
    "output_text",
    is_flag=True,
    help="Also request text output explaining the generation",
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
def generate(
    prompt: str | None,
    output: str,
    input_images: tuple[str, ...],
    labels: tuple[str, ...],
    model: str | None,
    temperature: float | None,
    output_text: bool,
    aspect_ratio: str | None,
    trace: bool | None,
    tags: tuple[str, ...],
    json_mode: bool,
) -> None:
    """
    Generate images from text prompts.

    PROMPT can be provided as an argument or piped via stdin.

    \b
    Examples:
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

        # Save to S3
        imagen generate "a sunset" -o s3://my-bucket/sunset.png

        # Get JSON output
        imagen generate "a mountain" -o mountain.png --json

        # With aspect ratio
        imagen generate "landscape" -o wide.png --aspect-ratio 16:9

    \b
    Notes:
        - Input images can be local paths, S3 URIs, or HTTP URLs
        - Output can be local path or S3 URI
        - Use --label to provide context for each input image
        - Temperature: 0.0 = consistent, 1.0 = creative
    """
    try:
        # Get prompt from args or stdin
        prompt_text = get_prompt_from_args_or_stdin(prompt)

        # Validate output path
        output = validate_output_path(output)

        # Validate input images
        validated_inputs = []
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
            model = cfg.get_default_model()

        # Get tracing setting
        if trace is None:
            trace = cfg.get_langsmith_tracing()

        # Show progress
        if not json_mode:
            show_progress("Generating image")

        # Create generator
        generator = GeminiImageGenerator(
            model_name=model,
            api_key=api_key,
            log_images=trace,
        )

        # Build generation parameters
        gen_params = {
            "prompt": prompt_text,
            "output_images": [output],
        }

        if validated_inputs:
            gen_params["input_images"] = validated_inputs

        if temperature is not None:
            gen_params["temperature"] = temperature

        if output_text:
            gen_params["output_text"] = True

        if aspect_ratio:
            gen_params["aspect_ratio"] = aspect_ratio

        if tags:
            gen_params["tags"] = list(tags)

        # Generate
        result = generator.generate(**gen_params)

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

            if output_text and result.text:
                output_data["text"] = result.text

            output_json(output_data)
        else:
            echo_success(f"Generated image saved to: {result.image_location}")
            echo_info(f"Model: {model}")

            if result.image_s3_uri:
                echo_info(f"S3 URI: {result.image_s3_uri}")

            if result.image_http_url:
                echo_info(f"URL: {result.image_http_url}")

            if output_text and result.text:
                click.echo()
                click.echo("Text output:")
                click.echo(result.text)

    except click.ClickException:
        raise
    except Exception as e:
        if not json_mode:
            clear_progress()
        error_msg = format_api_error(e)
        echo_error(error_msg, json_mode=json_mode)
        sys.exit(1)
