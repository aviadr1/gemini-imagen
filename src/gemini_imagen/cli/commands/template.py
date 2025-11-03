"""
Template management commands for gemini-imagen CLI.
"""

import json
import logging
import sys
from pathlib import Path

import click

from ..templates import (
    delete_template,
    get_template_path,
    list_templates,
    load_template,
    save_template,
)
from ..utils import echo_error, echo_info, echo_success, output_json
from ..variable_substitution import find_template_variables

logger = logging.getLogger(__name__)


@click.group()
def template() -> None:
    """Manage job templates."""
    pass


@template.command("save")
@click.argument("name")
@click.option(
    "--from-json",
    "json_file",
    type=click.Path(exists=True),
    required=True,
    help="JSON file to save as template",
)
def template_save(name: str, json_file: str) -> None:
    """
    Save a JSON file as a template.

    \b
    Examples:
        imagen template save thumbnail --from-json template.json
    """
    logger.info(f"Saving template '{name}' from {json_file}")

    try:
        # Load JSON file
        with Path(json_file).open() as f:
            template_data = json.load(f)

        # Save template
        path = save_template(name, template_data)

        echo_success(f"Template '{name}' saved")
        echo_info(f"Location: {path}")

    except json.JSONDecodeError as e:
        echo_error(f"Invalid JSON in file: {e}")
        sys.exit(1)
    except Exception as e:
        echo_error(f"Failed to save template: {e}")
        sys.exit(1)


@template.command("load")
@click.argument("name")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
def template_load(name: str, json_mode: bool) -> None:
    """
    Load and display a template.

    \b
    Examples:
        imagen template load thumbnail
        imagen template load thumbnail --json
    """
    logger.info(f"Loading template '{name}'")

    try:
        template_data = load_template(name)

        if json_mode:
            output_json(template_data)
        else:
            click.echo(json.dumps(template_data, indent=2))

    except FileNotFoundError:
        echo_error(f"Template '{name}' not found")
        sys.exit(1)
    except Exception as e:
        echo_error(f"Failed to load template: {e}")
        sys.exit(1)


@template.command("list")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
def template_list(json_mode: bool) -> None:
    """
    List all available templates.

    \b
    Examples:
        imagen template list
        imagen template list --json
    """
    logger.info("Listing templates")

    try:
        templates = list_templates()

        if json_mode:
            output_json({"templates": templates})
        else:
            if not templates:
                echo_info("No templates found")
                echo_info("Create one with: imagen template save NAME --from-json FILE")
            else:
                click.echo(f"Available templates ({len(templates)}):")
                for tmpl_name in templates:
                    echo_info(f"  {tmpl_name}")

    except Exception as e:
        echo_error(f"Failed to list templates: {e}")
        sys.exit(1)


@template.command("show")
@click.argument("name")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
def template_show(name: str, json_mode: bool) -> None:
    """
    Show template details including variables used.

    \b
    Examples:
        imagen template show thumbnail
    """
    logger.info(f"Showing template '{name}'")

    try:
        template_data = load_template(name)
        variables = find_template_variables(template_data)

        if json_mode:
            output_json({"template": template_data, "variables": variables})
        else:
            click.echo(f"Template: {name}")
            click.echo(f"Location: {get_template_path(name)}")
            click.echo()

            if variables:
                click.echo("Variables used:")
                for field, vars_list in variables.items():
                    click.echo(f"  {field}: {', '.join(vars_list)}")
                click.echo()

            click.echo("Content:")
            click.echo(json.dumps(template_data, indent=2))

    except FileNotFoundError:
        echo_error(f"Template '{name}' not found")
        sys.exit(1)
    except Exception as e:
        echo_error(f"Failed to show template: {e}")
        sys.exit(1)


@template.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to delete this template?")
def template_delete(name: str) -> None:
    """
    Delete a template.

    \b
    Examples:
        imagen template delete thumbnail
    """
    logger.info(f"Deleting template '{name}'")

    try:
        if delete_template(name):
            echo_success(f"Template '{name}' deleted")
        else:
            echo_error(f"Template '{name}' not found")
            sys.exit(1)

    except Exception as e:
        echo_error(f"Failed to delete template: {e}")
        sys.exit(1)


@template.command("path")
@click.argument("name")
def template_path(name: str) -> None:
    """
    Show the path to a template file.

    \b
    Examples:
        imagen template path thumbnail
    """
    try:
        path = get_template_path(name)
        click.echo(path)
    except Exception as e:
        echo_error(f"Failed to get template path: {e}")
        sys.exit(1)
