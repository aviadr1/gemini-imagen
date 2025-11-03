"""
LangSmith command for gemini-imagen CLI.

Export and manage traces from LangSmith.
"""

import json
import logging
import sys
from pathlib import Path

import click

from ..langsmith_client import extract_imagen_params, fetch_trace_from_url
from ..langsmith_utils import split_template_from_trace
from ..templates import save_template
from ..utils import echo_error, echo_success, output_json

logger = logging.getLogger(__name__)


@click.group()
def langsmith() -> None:
    """
    LangSmith integration commands.

    Export traces from LangSmith and convert them to templates and keys files.

    \b
    Examples:
        # Export trace as JSON
        imagen langsmith export TRACE_URL

        # Split into template and keys
        imagen langsmith export TRACE_URL --split

        # Save template directly
        imagen langsmith export TRACE_URL --save-template thumbnail

        # Save keys to file
        imagen langsmith export TRACE_URL --split --save-keys episode-123.json
    """


@langsmith.command()
@click.argument("trace_url")
@click.option(
    "--split",
    is_flag=True,
    help="Split into template (structure) and keys (data)",
)
@click.option(
    "--save-template",
    "template_name",
    help="Save template with this name",
)
@click.option(
    "--save-keys",
    "keys_file",
    type=click.Path(),
    help="Save keys to this file",
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Output result as JSON",
)
def export(
    trace_url: str,
    split: bool,
    template_name: str | None,
    keys_file: str | None,
    json_mode: bool,
) -> None:
    """
    Export a trace from LangSmith.

    TRACE_URL can be:
    - Full LangSmith trace URL (https://smith.langchain.com/...)
    - Just a run ID

    \b
    Examples:
        # Export full trace
        imagen langsmith export https://smith.langchain.com/public/abc/r/def

        # Export and split
        imagen langsmith export TRACE_URL --split

        # Save template directly
        imagen langsmith export TRACE_URL --save-template thumbnail

        # Save both template and keys
        imagen langsmith export TRACE_URL --save-template base --save-keys keys.json

        # JSON output
        imagen langsmith export TRACE_URL --json

    \b
    Notes:
        - Requires LANGSMITH_API_KEY environment variable
        - --split separates template (structure) from keys (data)
        - Template contains prompts with {variable} placeholders
        - Keys contain actual values for variables
        - Content within triple backticks (```) is treated as variables
    """
    try:
        logger.info(f"Exporting trace from LangSmith: {trace_url}")

        # Fetch trace
        if not json_mode:
            click.echo("Fetching trace from LangSmith...")

        trace_data = fetch_trace_from_url(trace_url)
        logger.debug(f"Fetched trace with {len(trace_data)} keys")

        # Extract gemini-imagen parameters
        params = extract_imagen_params(trace_data)
        logger.info(f"Extracted {len(params)} parameters")

        if not params:
            echo_error(
                "No gemini-imagen parameters found in trace.\\n"
                "Make sure the trace contains inputs/outputs from gemini-imagen.",
                json_mode=json_mode,
            )
            sys.exit(1)

        # Handle split mode
        if split or template_name or keys_file:
            logger.info("Splitting trace into template and keys")
            template, keys = split_template_from_trace(params)

            # Save template if requested
            if template_name:
                logger.info(f"Saving template: {template_name}")
                save_template(template_name, template)
                if not json_mode:
                    echo_success(f"Template saved: {template_name}")

            # Save keys if requested
            if keys_file:
                logger.info(f"Saving keys to: {keys_file}")
                keys_path = Path(keys_file)
                keys_path.write_text(json.dumps(keys, indent=2))
                if not json_mode:
                    echo_success(f"Keys saved to: {keys_file}")

            # Output results
            if json_mode:
                output_json(
                    {
                        "success": True,
                        "template": template,
                        "keys": keys,
                    }
                )
            elif not template_name and not keys_file:
                # Show split results
                click.echo()
                click.echo("=== Template ===")
                click.echo(json.dumps(template, indent=2))
                click.echo()
                click.echo("=== Keys ===")
                click.echo(json.dumps(keys, indent=2))
        else:
            # Output full params
            if json_mode:
                output_json(
                    {
                        "success": True,
                        "parameters": params,
                    }
                )
            else:
                click.echo(json.dumps(params, indent=2))

        logger.info("Export completed successfully")

    except ValueError as e:
        echo_error(str(e), json_mode=json_mode)
        logger.exception("Export failed")
        sys.exit(1)
    except Exception as e:
        echo_error(f"Failed to export trace: {e}", json_mode=json_mode)
        logger.exception("Export failed")
        sys.exit(1)
