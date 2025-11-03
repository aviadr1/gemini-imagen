"""
Configuration command for gemini-imagen CLI.

Provides commands to view and modify configuration.
"""

import click

from ...constants import (
    CONFIG_KEY_LANGSMITH_TRACING,
    CONFIG_KEY_SAFETY_SETTINGS,
    CONFIG_KEY_TEMPERATURE,
    SAFETY_PRESETS,
    HarmCategory,
)
from ..config import get_config
from ..utils import echo_error, echo_info, echo_success, output_json


@click.group()
def config() -> None:
    """View and modify configuration."""
    pass


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """
    Set a configuration value.

    \b
    Common keys:
        google_api_key              - Google Gemini API key
        aws_access_key_id           - AWS Access Key ID
        aws_secret_access_key       - AWS Secret Access Key
        aws_storage_bucket_name     - Default S3 bucket
        langsmith_api_key           - LangSmith API key
        langsmith_project           - LangSmith project name
        langsmith_tracing           - Enable LangSmith tracing (true/false)
        default_model               - Default model to use
        temperature                 - Default temperature (0.0-1.0)
        aspect_ratio                - Default aspect ratio (e.g., "16:9", "1:1")
        safety_settings             - Default safety preset (strict/default/relaxed/none)

    \b
    Examples:
        imagen config set default_model gemini-2.0-flash-exp
        imagen config set langsmith_tracing true
        imagen config set temperature 0.8
        imagen config set aspect_ratio 16:9
        imagen config set safety_settings relaxed
    """
    cfg = get_config()

    # Special handling for different key types
    parsed_value: str | bool | float | list[dict[str, str]]

    # Boolean values
    if key == CONFIG_KEY_LANGSMITH_TRACING and value.lower() in ("true", "false"):
        parsed_value = value.lower() == "true"

    # Float values
    elif key == CONFIG_KEY_TEMPERATURE:
        try:
            parsed_value = float(value)
            if not (0.0 <= parsed_value <= 1.0):
                echo_error("Temperature must be between 0.0 and 1.0")
                raise click.exceptions.Exit(1)
        except ValueError:
            echo_error(f"Invalid temperature value: {value}")
            raise click.exceptions.Exit(1)

    # Safety settings presets
    elif key == CONFIG_KEY_SAFETY_SETTINGS:
        preset = value.lower()
        if preset not in SAFETY_PRESETS:
            echo_error(
                f"Invalid safety preset: {value}. Valid values: {', '.join(SAFETY_PRESETS.keys())}"
            )
            raise click.exceptions.Exit(1)

        threshold = SAFETY_PRESETS[preset]
        # Store as list of dicts with string values that can be serialized to YAML
        parsed_value = [
            {
                "category": str(cat),
                "threshold": str(threshold),
            }
            for cat in [
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                HarmCategory.HARM_CATEGORY_HARASSMENT,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            ]
        ]

    # String values (default)
    else:
        parsed_value = value

    cfg.set(key, parsed_value)
    echo_success(f"Set {key} = {value}")
    echo_info(f"Config saved to: {cfg.get_path()}")


@config.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """
    Get a configuration value.

    \b
    Example:
        imagen config get default_model
    """
    cfg = get_config()
    value = cfg.get(key)

    if value is not None:
        click.echo(value)
    else:
        echo_error(f"Configuration key '{key}' not found")
        raise click.exceptions.Exit(1)


@config.command("list")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
def config_list(json_mode: bool) -> None:
    """
    List all configuration values.

    \b
    Example:
        imagen config list
        imagen config list --json
    """
    cfg = get_config()
    all_config = cfg.list_all()

    if json_mode:
        output_json(all_config)
    else:
        if not all_config:
            echo_info("No configuration values set")
            click.echo()
            echo_info(f"Config file: {cfg.get_path()}")
            echo_info("Set values with: imagen config set KEY VALUE")
            return

        click.echo("Configuration:")
        for key, value in all_config.items():
            # Mask sensitive values
            if (
                ("key" in key.lower() or "secret" in key.lower())
                and isinstance(value, str)
                and len(value) > 8
            ):
                value = value[:8] + "..."
            echo_info(f"{key}: {value}")

        click.echo()
        echo_info(f"Config file: {cfg.get_path()}")


@config.command("delete")
@click.argument("key")
@click.confirmation_option(prompt="Are you sure you want to delete this configuration?")
def config_delete(key: str) -> None:
    """
    Delete a configuration value.

    \b
    Example:
        imagen config delete default_model
    """
    cfg = get_config()

    if cfg.delete(key):
        echo_success(f"Deleted configuration: {key}")
    else:
        echo_error(f"Configuration key '{key}' not found")
        raise click.exceptions.Exit(1)


@config.command("path")
def config_path() -> None:
    """
    Show the path to the configuration file.

    \b
    Example:
        imagen config path
    """
    cfg = get_config()
    click.echo(cfg.get_path())
