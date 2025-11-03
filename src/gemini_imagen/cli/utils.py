"""
Utility functions for gemini-imagen CLI.

Provides output formatting, error handling, and helper functions.
"""

import json
import sys
from pathlib import Path
from typing import Any

import click


def filter_none_values(d: dict[str, Any]) -> dict[str, Any]:
    """
    Filter out keys with None values from a dictionary.

    This is useful for cleaning up kwargs before passing to functions,
    especially for LangSmith tracing where we don't want to log unused parameters.

    Args:
        d: Dictionary to filter

    Returns:
        New dictionary with None values removed

    Examples:
        >>> filter_none_values({"a": 1, "b": None, "c": 3})
        {'a': 1, 'c': 3}
        >>> filter_none_values({"prompt": "test", "temperature": None})
        {'prompt': 'test'}
    """
    return {k: v for k, v in d.items() if v is not None}


def is_tty() -> bool:
    """Check if output is a TTY (terminal)."""
    return sys.stdout.isatty()


def should_use_color() -> bool:
    """
    Determine if color output should be used.

    Checks:
    - Output is a TTY
    - NO_COLOR environment variable is not set
    - TERM is not 'dumb'
    """
    import os

    if not is_tty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return os.environ.get("TERM") != "dumb"


def echo_success(message: str, json_mode: bool = False) -> None:
    """
    Print success message.

    Args:
        message: Message to print
        json_mode: If True, suppress output (JSON will be output separately)
    """
    if json_mode:
        return
    if should_use_color():
        click.secho(f"✓ {message}", fg="green")
    else:
        click.echo(f"✓ {message}")


def echo_info(message: str, json_mode: bool = False) -> None:
    """
    Print info message.

    Args:
        message: Message to print
        json_mode: If True, suppress output (JSON will be output separately)
    """
    if json_mode:
        return
    click.echo(f"  {message}")


def echo_warning(message: str, json_mode: bool = False) -> None:
    """
    Print warning message.

    Args:
        message: Message to print
        json_mode: If True, suppress output to stderr
    """
    if json_mode:
        return
    if should_use_color():
        click.secho(f"⚠ {message}", fg="yellow", err=True)
    else:
        click.echo(f"⚠ {message}", err=True)


def echo_error(message: str, json_mode: bool = False) -> None:
    """
    Print error message.

    Args:
        message: Message to print
        json_mode: If True, format as JSON error
    """
    if json_mode:
        output_json({"error": message, "success": False})
    else:
        if should_use_color():
            click.secho(f"✗ Error: {message}", fg="red", err=True)
        else:
            click.echo(f"✗ Error: {message}", err=True)


def output_json(data: dict[str, Any]) -> None:
    """
    Output data as JSON.

    Args:
        data: Data to output as JSON
    """
    click.echo(json.dumps(data, indent=2))


def validate_output_path(path: str, allow_s3: bool = True) -> str:
    """
    Validate output path.

    Args:
        path: Output path
        allow_s3: Whether to allow S3 URIs

    Returns:
        Validated path

    Raises:
        click.ClickException: If path is invalid
    """
    from ..s3_utils import is_s3_uri

    # Check if it's an S3 URI
    if is_s3_uri(path):
        if not allow_s3:
            raise click.ClickException("S3 URIs are not supported for this operation")
        return path

    # Check if it's a local path
    output_path = Path(path)

    # Check if parent directory exists
    if output_path.parent != Path() and not output_path.parent.exists():
        raise click.ClickException(
            f"Parent directory does not exist: {output_path.parent}\n"
            f"Create it first with: mkdir -p {output_path.parent}"
        )

    return path


def validate_input_path(path: str) -> str:
    """
    Validate input path.

    Args:
        path: Input path (can be local path, S3 URI, or HTTP URL)

    Returns:
        Validated path

    Raises:
        click.ClickException: If path is invalid
    """
    from ..s3_utils import is_http_url, is_s3_uri

    # S3 URIs and HTTP URLs are always valid (will be validated at runtime)
    if is_s3_uri(path) or is_http_url(path):
        return path

    # Check if local file exists
    input_path = Path(path)
    if not input_path.exists():
        raise click.ClickException(f"Input file does not exist: {path}")
    if not input_path.is_file():
        raise click.ClickException(f"Input path is not a file: {path}")

    return str(input_path)


def read_stdin() -> str:
    """
    Read from stdin.

    Returns:
        Content from stdin

    Raises:
        click.ClickException: If stdin is a TTY (no piped input)
    """
    if sys.stdin.isatty():
        raise click.ClickException(
            "No input provided. Either provide a prompt argument or pipe input via stdin."
        )
    return sys.stdin.read().strip()


def get_prompt_from_args_or_stdin(prompt: str | None) -> str:
    """
    Get prompt from arguments or stdin.

    Args:
        prompt: Prompt from arguments (or None)

    Returns:
        Prompt text

    Raises:
        click.ClickException: If no prompt provided
    """
    if prompt:
        return prompt

    # Try to read from stdin
    if not sys.stdin.isatty():
        return read_stdin()

    raise click.ClickException(
        "No prompt provided. Either provide a prompt argument or pipe input via stdin."
    )


def format_api_error(error: Exception) -> str:
    """
    Format API error message with helpful hints.

    Args:
        error: Exception from API call

    Returns:
        Formatted error message
    """
    error_str = str(error)

    # Check for common error patterns
    if "API key" in error_str or "authentication" in error_str.lower():
        return (
            f"{error_str}\n\n"
            "Hint: Set your Google API key with:\n"
            "  imagen keys set google YOUR_KEY\n"
            "Or set the GOOGLE_API_KEY environment variable."
        )

    if "quota" in error_str.lower() or "rate limit" in error_str.lower():
        return (
            f"{error_str}\n\n"
            "Hint: You've hit the API rate limit. Wait a moment and try again.\n"
            "Free tier limits: 10 requests/minute, 1500 requests/day"
        )

    if "bucket" in error_str.lower() and "s3" in error_str.lower():
        return (
            f"{error_str}\n\n"
            "Hint: Configure your S3 credentials with:\n"
            "  imagen keys set aws-access-key YOUR_KEY\n"
            "  imagen keys set aws-secret-key YOUR_SECRET\n"
            "  imagen config set aws_storage_bucket_name YOUR_BUCKET"
        )

    return error_str


def show_progress(message: str) -> None:
    """
    Show progress message.

    Args:
        message: Progress message
    """
    if is_tty():
        click.echo(f"{message}...", nl=False)
        sys.stdout.flush()


def clear_progress() -> None:
    """Clear progress message."""
    if is_tty():
        # Move cursor to beginning of line and clear
        click.echo("\r\033[K", nl=False)
