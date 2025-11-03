"""
Generate command for gemini-imagen CLI.

Generates images from text prompts.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import click

from ...constants import SAFETY_PRESETS, HarmBlockThreshold, HarmCategory, SafetySetting
from ...gemini_image_wrapper import GeminiImageGenerator
from ...models import GenerateParams, ImageSource
from ..config import get_config
from ..job_merge import merge_template_keys_overrides, split_job_and_variables
from ..templates import load_template
from ..utils import (
    clear_progress,
    echo_error,
    echo_info,
    echo_success,
    format_api_error,
    format_brief_error,
    get_prompt_from_args_or_stdin,
    output_json,
    show_progress,
    validate_input_path,
    validate_output_path,
)
from ..variable_substitution import substitute_variables, validate_variables

logger = logging.getLogger(__name__)


def parse_safety_setting(setting_str: str) -> list[SafetySetting]:
    """
    Parse a safety setting string into a list of SafetySetting objects.

    Formats supported:
    - preset:THRESHOLD (e.g., "preset:relaxed")
    - CATEGORY:THRESHOLD (e.g., "SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH")

    Args:
        setting_str: Safety setting string

    Returns:
        List of SafetySetting objects

    Raises:
        ValueError: If format is invalid
    """
    if ":" not in setting_str:
        raise ValueError(
            f"Invalid safety setting format: {setting_str}. "
            "Use CATEGORY:THRESHOLD or preset:THRESHOLD"
        )

    category_part, threshold_part = setting_str.split(":", 1)

    # Parse threshold
    threshold: Any
    if threshold_part.lower() in SAFETY_PRESETS:
        threshold = SAFETY_PRESETS[threshold_part.lower()]
    else:
        # Try to get enum by name
        threshold_name = (
            threshold_part if threshold_part.startswith("BLOCK_") else f"BLOCK_{threshold_part}"
        )
        try:
            threshold = getattr(HarmBlockThreshold, threshold_name)
        except AttributeError:
            raise ValueError(
                f"Invalid threshold: {threshold_part}. "
                f"Valid values: {', '.join(SAFETY_PRESETS.keys())}, "
                "BLOCK_NONE, BLOCK_ONLY_HIGH, BLOCK_MEDIUM_AND_ABOVE, BLOCK_LOW_AND_ABOVE"
            )

    # Parse category
    if category_part.lower() == "preset":
        # Apply to all categories
        return [
            SafetySetting(category=cat, threshold=threshold)
            for cat in [
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                HarmCategory.HARM_CATEGORY_HARASSMENT,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            ]
        ]
    else:
        # Specific category
        category_name = (
            category_part
            if category_part.startswith("HARM_CATEGORY_")
            else f"HARM_CATEGORY_{category_part}"
        )
        try:
            category = getattr(HarmCategory, category_name)
        except AttributeError:
            raise ValueError(
                f"Invalid category: {category_part}. "
                "Valid values: SEXUALLY_EXPLICIT, DANGEROUS_CONTENT, HARASSMENT, HATE_SPEECH, CIVIC_INTEGRITY"
            )

        return [SafetySetting(category=category, threshold=threshold)]


@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--template",
    "template_name",
    help="Load job template by name",
)
@click.option(
    "--keys",
    "keys_files",
    multiple=True,
    type=click.Path(exists=True),
    help="Load keys from JSON file (can specify multiple, applied in order)",
)
@click.option(
    "--var",
    "variables",
    multiple=True,
    help="Set variable value (format: NAME=VALUE, can specify multiple)",
)
@click.option(
    "-s",
    "--system-prompt",
    "system_prompt",
    help="System prompt (use @file.txt to read from file)",
)
@click.option(
    "--dump-job",
    is_flag=True,
    help="Output final job JSON and exit (don't execute)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be executed without running",
)
@click.option("-o", "--output", help="Output file path or S3 URI")
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
    "--safety-setting",
    "safety_settings",
    multiple=True,
    help=(
        "Safety filtering threshold. Format: CATEGORY:THRESHOLD or preset:THRESHOLD. "
        "Presets: strict, default, relaxed, none. "
        "Example: --safety-setting preset:relaxed or --safety-setting SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH"
    ),
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Output result as JSON",
)
@click.pass_context
def generate(
    ctx: click.Context,
    prompt: str | None,
    template_name: str | None,
    keys_files: tuple[str, ...],
    variables: tuple[str, ...],
    system_prompt: str | None,
    dump_job: bool,
    dry_run: bool,
    output: str | None,
    input_images: tuple[str, ...],
    labels: tuple[str, ...],
    model: str | None,
    temperature: float | None,
    output_text: bool,
    aspect_ratio: str | None,
    trace: bool | None,
    tags: tuple[str, ...],
    safety_settings: tuple[str, ...],
    json_mode: bool,
) -> None:
    """
    Generate images from text prompts.

    PROMPT can be provided as an argument or piped via stdin.

    \b
    Examples:
        # Basic generation
        imagen generate "a serene landscape" -o output.png

        # Using template + keys (FAST ITERATION!)
        imagen generate --template thumbnail --keys episode.json -p "New prompt"

        # With variable overrides
        imagen generate --template thumbnail --keys episode.json --var show_info='{"title":"..."}'

        # System prompt
        imagen generate "test" -o output.png -s "You are an expert"

        # Dump job to see what would be executed
        imagen generate --template thumbnail --keys episode.json --dump-job

        # Dry run
        imagen generate --template thumbnail --keys episode.json --dry-run

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

    \b
    Notes:
        - Template + keys enable fast iteration on prompts
        - Variables in templates use {variable_name} syntax
        - CLI flags override template/keys values
        - Input images can be local paths, S3 URIs, or HTTP URLs
        - Output can be local path or S3 URI
        - Use --label to provide context for each input image
        - Set global defaults with: imagen config set KEY VALUE
        - Supported config defaults: temperature, aspect_ratio, safety_settings
    """
    try:
        logger.info("Starting generate command with template/keys system")

        # Step 1: Load template if specified
        template = None
        if template_name:
            logger.info(f"Loading template: {template_name}")
            try:
                template = load_template(template_name)
                logger.debug(f"Template loaded with {len(template)} keys")
            except FileNotFoundError:
                echo_error(f"Template '{template_name}' not found", json_mode=json_mode)
                sys.exit(1)

        # Step 2: Load keys files
        keys_list = []
        for keys_file in keys_files:
            logger.info(f"Loading keys file: {keys_file}")
            try:
                with Path(keys_file).open() as f:
                    keys_data = json.load(f)
                keys_list.append(keys_data)
                logger.debug(f"Keys file loaded with {len(keys_data)} keys")
            except json.JSONDecodeError as e:
                echo_error(f"Invalid JSON in {keys_file}: {e}", json_mode=json_mode)
                sys.exit(1)

        # Step 3: Parse --var variables
        var_dict = {}
        for var in variables:
            if "=" not in var:
                echo_error(f"Invalid variable format: {var}. Use NAME=VALUE", json_mode=json_mode)
                sys.exit(1)
            name, value = var.split("=", 1)
            var_dict[name.strip()] = value.strip()
            logger.debug(f"Variable: {name} = {value[:50]}...")

        # Step 4: Handle system_prompt with @file support
        if system_prompt and system_prompt.startswith("@"):
            # Read from file
            file_path = Path(system_prompt[1:])
            if not file_path.exists():
                echo_error(f"System prompt file not found: {file_path}", json_mode=json_mode)
                sys.exit(1)
            system_prompt = file_path.read_text()
            logger.debug(f"System prompt loaded from file: {file_path}")

        # Step 5: Build CLI overrides dict
        cli_overrides: dict[str, Any] = {}

        # Handle prompt (from CLI arg or stdin, but not required if in template/keys)
        if prompt is not None:
            cli_overrides["prompt"] = prompt
        elif not sys.stdin.isatty() and not template_name:
            # Try stdin only if no template
            cli_overrides["prompt"] = get_prompt_from_args_or_stdin(None)

        if system_prompt:
            cli_overrides["system_prompt"] = system_prompt

        if output:
            cli_overrides["output_images"] = [validate_output_path(output)]

        # Handle input images
        if input_images:
            validated_inputs: list[ImageSource] = []
            for i, input_path in enumerate(input_images):
                validated_path = validate_input_path(input_path)
                if i < len(labels):
                    validated_inputs.append((labels[i], validated_path))
                else:
                    validated_inputs.append(validated_path)
            cli_overrides["input_images"] = validated_inputs

        if model is not None:
            cli_overrides["model"] = model

        if temperature is not None:
            cli_overrides["temperature"] = temperature

        if output_text:
            cli_overrides["output_text"] = True

        if aspect_ratio:
            cli_overrides["aspect_ratio"] = aspect_ratio

        if trace is not None:
            cli_overrides["trace"] = trace

        if tags:
            cli_overrides["tags"] = list(tags)

        # Parse safety settings
        if safety_settings:
            parsed_settings: list[SafetySetting] = []
            for setting_str in safety_settings:
                try:
                    settings_list = parse_safety_setting(setting_str)
                    parsed_settings.extend(settings_list)
                except ValueError as e:
                    echo_error(str(e), json_mode=json_mode)
                    sys.exit(1)
            cli_overrides["safety_settings"] = parsed_settings

        # Add --var variables to CLI overrides
        cli_overrides.update(var_dict)

        logger.info(f"CLI overrides: {len(cli_overrides)} keys")

        # Step 6: Merge template + keys + CLI overrides
        logger.info("Merging template, keys, and CLI overrides")
        merged = merge_template_keys_overrides(
            template=template,
            keys=keys_list if keys_list else None,
            cli_overrides=cli_overrides if cli_overrides else None,
        )
        logger.debug(f"Merged job has {len(merged)} keys")

        # Step 7: Split into library params and variables
        logger.info("Splitting job into library params and variables")
        lib_params, var_values = split_job_and_variables(merged)
        logger.debug(f"Library params: {len(lib_params)}, Variables: {len(var_values)}")

        # Step 8: Validate and substitute variables
        logger.info("Validating and substituting variables")
        is_valid, missing = validate_variables(lib_params, var_values)
        if not is_valid:
            echo_error(
                f"Missing required variables: {', '.join(missing)}\n"
                f"Provide them with --var NAME=VALUE or in keys file",
                json_mode=json_mode,
            )
            sys.exit(1)

        final_job = substitute_variables(lib_params, var_values)
        logger.info(f"Final job ready with {len(final_job)} parameters")

        # Step 9: Handle --dump-job
        if dump_job:
            logger.info("Dumping job JSON (--dump-job mode)")
            output_json(final_job)
            return

        # Step 10: Handle --dry-run
        if dry_run:
            logger.info("Dry run mode - showing job without executing")
            click.echo("Would execute the following job:")
            click.echo()
            click.echo(json.dumps(final_job, indent=2))
            return

        # Step 11: Execute normally
        logger.info("Executing job")

        # Check required fields
        if "prompt" not in final_job:
            echo_error(
                "No prompt provided. Provide via:\n"
                "  - CLI argument: imagen generate 'prompt' ...\n"
                "  - Stdin: echo 'prompt' | imagen generate ...\n"
                "  - Template/keys: with prompt field\n"
                "  - --var: --var prompt='...'",
                json_mode=json_mode,
            )
            sys.exit(1)

        if "output_images" not in final_job:
            echo_error(
                "No output specified. Provide with -o OUTPUT or in template/keys",
                json_mode=json_mode,
            )
            sys.exit(1)

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

        # Get model (from final_job or config)
        model_name = final_job.pop("model", None) or cfg.get_generation_model()

        # Get tracing setting (from final_job or config)
        trace_enabled = final_job.pop("trace", None)
        if trace_enabled is None:
            trace_enabled = cfg.get_langsmith_tracing()

        # Apply config defaults for parameters not specified
        if "temperature" not in final_job and cfg.get_temperature() is not None:
            final_job["temperature"] = cfg.get_temperature()

        if "aspect_ratio" not in final_job and cfg.get_aspect_ratio() is not None:
            final_job["aspect_ratio"] = cfg.get_aspect_ratio()

        if "safety_settings" not in final_job and cfg.get_safety_settings() is not None:
            # Convert config safety settings (list of dicts) to SafetySetting objects
            config_safety = cfg.get_safety_settings()
            if config_safety:
                final_job["safety_settings"] = [
                    SafetySetting(
                        category=getattr(
                            HarmCategory,
                            s["category"].replace("HarmCategory.", ""),
                        ),
                        threshold=getattr(
                            HarmBlockThreshold,
                            s["threshold"].replace("HarmBlockThreshold.", ""),
                        ),
                    )
                    for s in config_safety
                ]

        # Show progress
        if not json_mode:
            show_progress("Generating image")

        # Create generator
        generator = GeminiImageGenerator(
            model_name=model_name,
            api_key=api_key,
            log_images=trace_enabled,
        )

        # Generate (final_job now only contains library params)
        # Use Pydantic model for type safety and automatic None filtering
        params = GenerateParams(**final_job)
        logger.debug(
            f"Calling generator.generate() with: {list(params.model_dump(exclude_none=True).keys())}"
        )
        result = asyncio.run(generator.generate(params))

        # Clear progress
        if not json_mode:
            clear_progress()

        logger.info("Generation completed successfully")

        # Output results
        if json_mode:
            output_data = {
                "success": True,
                "image_path": result.image_location,
                "model": model_name,
            }

            if result.image_s3_uri:
                output_data["s3_uri"] = result.image_s3_uri

            if result.image_http_url:
                output_data["http_url"] = result.image_http_url

            if final_job.get("output_text") and result.text:
                output_data["text"] = result.text

            output_json(output_data)
        else:
            echo_success(f"Generated image saved to: {result.image_location}")
            echo_info(f"Model: {model_name}")

            if result.image_s3_uri:
                echo_info(f"S3 URI: {result.image_s3_uri}")

            if result.image_http_url:
                echo_info(f"URL: {result.image_http_url}")

            if final_job.get("output_text") and result.text:
                click.echo()
                click.echo("Text output:")
                click.echo(result.text)

    except click.ClickException:
        raise
    except Exception as e:
        if not json_mode:
            clear_progress()

        # Get verbose flag from context
        verbose = ctx.obj.get("verbose", False) if ctx.obj else False

        # Format error based on verbosity
        error_msg = format_api_error(e, verbose=verbose)
        echo_error(error_msg, json_mode=json_mode)

        # Only log full traceback if verbose
        if verbose:
            logger.exception("Generate command failed")
        else:
            logger.error(f"Generate command failed: {format_brief_error(e)}")

        sys.exit(1)
