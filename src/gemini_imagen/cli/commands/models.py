"""
Models command for gemini-imagen CLI.

Provides commands to list and manage models.
"""

import click

from ..config import get_config
from ..utils import echo_info, echo_success


@click.group()
def models() -> None:
    """List and manage models."""
    pass


@models.command("list")
def models_list() -> None:
    """
    List available models.

    Shows the models that can be used with gemini-imagen.
    """
    click.echo("Available models:")
    echo_info("gemini-2.0-flash-exp - Fast experimental model (default)")
    echo_info("gemini-2.5-flash-image - Legacy image generation model")
    echo_info("gemini-2.0-flash - Standard flash model")
    click.echo()
    echo_info("Use with: imagen generate 'prompt' -m MODEL_NAME -o output.png")


@models.command("default")
@click.argument("model_name", required=False)
def models_default(model_name: str | None) -> None:
    """
    Get or set the default model.

    \b
    Examples:
        imagen models default                      # Show current default
        imagen models default gemini-2.0-flash-exp # Set new default
    """
    cfg = get_config()

    if model_name is None:
        # Show current default
        current = cfg.get_default_model()
        click.echo(f"Default model: {current}")
    else:
        # Set new default
        cfg.set("default_model", model_name)
        echo_success(f"Set default model to: {model_name}")
        echo_info(f"Config saved to: {cfg.get_path()}")
