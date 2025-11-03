"""
Storage commands for gemini-imagen CLI.

Provides upload and download commands for S3 storage.
"""

import asyncio
import sys
from pathlib import Path

import click
from PIL import Image

from ...s3_utils import download_from_s3, is_s3_uri, parse_s3_uri, upload_to_s3
from ..config import get_config
from ..utils import (
    clear_progress,
    echo_error,
    echo_info,
    echo_success,
    format_api_error,
    output_json,
    show_progress,
    validate_input_path,
)


@click.command()
@click.argument("source")
@click.argument("destination")
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Output result as JSON",
)
def upload(source: str, destination: str, json_mode: bool) -> None:
    """
    Upload an image to S3.

    SOURCE must be a local file path.
    DESTINATION must be an S3 URI (s3://bucket/key).

    \b
    Examples:
        # Upload to S3
        imagen upload local.png s3://my-bucket/remote.png

        # Upload with JSON output
        imagen upload image.jpg s3://bucket/image.jpg --json

    \b
    Notes:
        - Requires AWS credentials to be configured
        - Use 'imagen keys set aws-access-key' and 'imagen keys set aws-secret-key'
        - Or set GV_AWS_ACCESS_KEY_ID and GV_AWS_SECRET_ACCESS_KEY environment variables
    """
    try:
        # Validate source is local file
        source = validate_input_path(source)
        source_path = Path(source)

        if not source_path.exists():
            echo_error(f"Source file does not exist: {source}", json_mode=json_mode)
            sys.exit(1)

        # Validate destination is S3 URI
        if not is_s3_uri(destination):
            echo_error(
                f"Destination must be an S3 URI (s3://bucket/key), got: {destination}",
                json_mode=json_mode,
            )
            sys.exit(1)

        # Parse S3 URI
        bucket, key = parse_s3_uri(destination)

        # Check AWS credentials
        cfg = get_config()
        if not cfg.get_aws_access_key_id() or not cfg.get_aws_secret_access_key():
            echo_error(
                "AWS credentials not configured.\n"
                "Set them with:\n"
                "  imagen keys set aws-access-key YOUR_KEY\n"
                "  imagen keys set aws-secret-key YOUR_SECRET\n"
                "Or set GV_AWS_ACCESS_KEY_ID and GV_AWS_SECRET_ACCESS_KEY environment variables.",
                json_mode=json_mode,
            )
            sys.exit(1)

        # Show progress
        if not json_mode:
            show_progress(f"Uploading {source_path.name} to S3")

        # Upload
        from PIL import Image

        image = Image.open(source_path)

        # Run async upload
        asyncio.run(upload_to_s3(image, bucket, key))

        # Clear progress
        if not json_mode:
            clear_progress()

        # Get HTTP URL
        from ...s3_utils import get_http_url

        http_url = get_http_url(bucket, key)

        # Output results
        if json_mode:
            output_json(
                {
                    "success": True,
                    "source": str(source_path),
                    "destination": destination,
                    "bucket": bucket,
                    "key": key,
                    "http_url": http_url,
                }
            )
        else:
            echo_success(f"Uploaded {source_path.name}")
            echo_info(f"S3 URI: {destination}")
            echo_info(f"URL: {http_url}")

    except click.ClickException:
        raise
    except Exception as e:
        if not json_mode:
            clear_progress()
        error_msg = format_api_error(e)
        echo_error(error_msg, json_mode=json_mode)
        sys.exit(1)


@click.command()
@click.argument("source")
@click.argument("destination")
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Output result as JSON",
)
def download(source: str, destination: str, json_mode: bool) -> None:
    """
    Download an image from S3.

    SOURCE must be an S3 URI (s3://bucket/key).
    DESTINATION must be a local file path.

    \b
    Examples:
        # Download from S3
        imagen download s3://my-bucket/remote.png local.png

        # Download with JSON output
        imagen download s3://bucket/image.jpg image.jpg --json

    \b
    Notes:
        - Requires AWS credentials to be configured
        - Use 'imagen keys set aws-access-key' and 'imagen keys set aws-secret-key'
        - Or set GV_AWS_ACCESS_KEY_ID and GV_AWS_SECRET_ACCESS_KEY environment variables
    """
    try:
        # Validate source is S3 URI
        if not is_s3_uri(source):
            echo_error(
                f"Source must be an S3 URI (s3://bucket/key), got: {source}",
                json_mode=json_mode,
            )
            sys.exit(1)

        # Parse S3 URI
        bucket, key = parse_s3_uri(source)

        # Validate destination
        dest_path = Path(destination)

        # Check if parent directory exists
        if dest_path.parent != Path() and not dest_path.parent.exists():
            echo_error(
                f"Parent directory does not exist: {dest_path.parent}\n"
                f"Create it first with: mkdir -p {dest_path.parent}",
                json_mode=json_mode,
            )
            sys.exit(1)

        # Check AWS credentials
        cfg = get_config()
        if not cfg.get_aws_access_key_id() or not cfg.get_aws_secret_access_key():
            echo_error(
                "AWS credentials not configured.\n"
                "Set them with:\n"
                "  imagen keys set aws-access-key YOUR_KEY\n"
                "  imagen keys set aws-secret-key YOUR_SECRET\n"
                "Or set GV_AWS_ACCESS_KEY_ID and GV_AWS_SECRET_ACCESS_KEY environment variables.",
                json_mode=json_mode,
            )
            sys.exit(1)

        # Show progress
        if not json_mode:
            show_progress(f"Downloading {key.split('/')[-1]} from S3")

        # Download
        image = asyncio.run(download_from_s3(bucket, key))

        # Save locally (download_from_s3 returns Image when local_path is None)
        assert isinstance(image, Image.Image), "Expected PIL Image from download_from_s3"
        image.save(dest_path)

        # Clear progress
        if not json_mode:
            clear_progress()

        # Output results
        if json_mode:
            output_json(
                {
                    "success": True,
                    "source": source,
                    "destination": str(dest_path),
                    "bucket": bucket,
                    "key": key,
                }
            )
        else:
            echo_success(f"Downloaded to {dest_path}")
            echo_info(f"Source: {source}")

    except click.ClickException:
        raise
    except Exception as e:
        if not json_mode:
            clear_progress()
        error_msg = format_api_error(e)
        echo_error(error_msg, json_mode=json_mode)
        sys.exit(1)
