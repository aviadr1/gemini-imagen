"""
Keys management command for gemini-imagen CLI.

Provides commands to set, list, and delete API keys.
"""

import click

from ..config import get_config
from ..utils import echo_error, echo_info, echo_success


@click.group()
def keys() -> None:
    """Manage API keys and credentials."""
    pass


@keys.command("set")
@click.argument("key_name", type=click.Choice(["google", "aws-access-key", "aws-secret-key"]))
@click.argument("value")
def keys_set(key_name: str, value: str) -> None:
    """
    Set an API key or credential.

    \b
    KEY_NAME can be:
        google          - Google Gemini API key
        aws-access-key  - AWS Access Key ID
        aws-secret-key  - AWS Secret Access Key

    \b
    Examples:
        imagen keys set google YOUR_GOOGLE_API_KEY
        imagen keys set aws-access-key YOUR_AWS_ACCESS_KEY
        imagen keys set aws-secret-key YOUR_AWS_SECRET_KEY
    """
    config = get_config()

    # Map friendly names to config keys
    key_mapping = {
        "google": "google_api_key",
        "aws-access-key": "aws_access_key_id",
        "aws-secret-key": "aws_secret_access_key",
    }

    config_key = key_mapping[key_name]
    config.set(config_key, value)

    # Mask the value in output for security
    masked_value = value[:8] + "..." if len(value) > 8 else "***"
    echo_success(f"Set {key_name} to {masked_value}")
    echo_info(f"Config saved to: {config.get_path()}")


@keys.command("list")
def keys_list() -> None:
    """
    List all configured keys (values are masked).

    Shows which keys are configured in the config file or environment variables.
    """
    config = get_config()

    # List of keys to check
    key_checks = [
        ("google_api_key", "Google API Key", config.get_google_api_key()),
        ("aws_access_key_id", "AWS Access Key ID", config.get_aws_access_key_id()),
        ("aws_secret_access_key", "AWS Secret Access Key", config.get_aws_secret_access_key()),
        ("aws_storage_bucket_name", "AWS S3 Bucket", config.get_aws_bucket_name()),
        ("langsmith_api_key", "LangSmith API Key", config.get_langsmith_api_key()),
    ]

    click.echo("Configured keys:")
    any_configured = False

    for config_key, display_name, value in key_checks:
        if value:
            # Mask the value
            if config_key == "aws_storage_bucket_name":
                # Don't mask bucket name
                masked = value
            else:
                masked = value[:8] + "..." if len(value) > 8 else "***"
            echo_info(f"{display_name}: {masked}")
            any_configured = True
        else:
            echo_info(f"{display_name}: (not set)")

    if any_configured:
        click.echo()
        echo_info(f"Config file: {config.get_path()}")
    else:
        click.echo()
        echo_info("No keys configured. Set keys with: imagen keys set KEY_NAME VALUE")


@keys.command("delete")
@click.argument("key_name", type=click.Choice(["google", "aws-access-key", "aws-secret-key"]))
@click.confirmation_option(prompt="Are you sure you want to delete this key?")
def keys_delete(key_name: str) -> None:
    """
    Delete an API key or credential.

    \b
    KEY_NAME can be:
        google          - Google Gemini API key
        aws-access-key  - AWS Access Key ID
        aws-secret-key  - AWS Secret Access Key

    \b
    Example:
        imagen keys delete google
    """
    config = get_config()

    # Map friendly names to config keys
    key_mapping = {
        "google": "google_api_key",
        "aws-access-key": "aws_access_key_id",
        "aws-secret-key": "aws_secret_access_key",
    }

    config_key = key_mapping[key_name]

    if config.delete(config_key):
        echo_success(f"Deleted {key_name}")
    else:
        echo_error(f"Key {key_name} was not set")
