"""
Main CLI entry point for gemini-imagen.

Provides a command-line interface for image generation and analysis using Google Gemini.
"""

import click

from .. import __version__
from .commands import (
    analyze,
    config_cmd,
    edit,
    generate,
    keys,
    langsmith,
    models,
    storage,
    template,
)


@click.group()
@click.version_option(version=__version__, prog_name="imagen")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    Imagen - Google Gemini Image Generation CLI

    A command-line interface for generating and analyzing images using Google Gemini.

    \b
    Quick Start:
        # Generate an image
        imagen generate "a serene landscape" -o output.png

        # Analyze an image
        imagen analyze image.jpg

        # Set up your API key
        imagen keys set google YOUR_API_KEY

    \b
    Examples:
        # Generate with temperature control
        imagen generate "a robot" -o robot.png --temperature 0.8

        # Use piped input
        echo "a cat" | imagen generate -o cat.png

        # Multiple input images for style blending
        imagen edit "blend these styles" -i style1.jpg -i style2.jpg -o result.png

        # Save to S3
        imagen generate "a sunset" -o s3://my-bucket/sunset.png

        # Get JSON output
        imagen analyze image.jpg --json

    \b
    Configuration:
        Config file: ~/.config/imagen/config.yaml
        View config: imagen config list
        Set values:  imagen config set KEY VALUE

    For more information, visit: https://github.com/aviadr1/gemini-imagen
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


cli.add_command(generate.generate)
cli.add_command(analyze.analyze)
cli.add_command(edit.edit)
cli.add_command(keys.keys)
cli.add_command(config_cmd.config)
cli.add_command(models.models)
cli.add_command(storage.upload)
cli.add_command(storage.download)
cli.add_command(template.template)
cli.add_command(langsmith.langsmith)


if __name__ == "__main__":
    cli()
