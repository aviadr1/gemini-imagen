"""
S3 Utility Functions for Image Storage
======================================

This module provides utilities for uploading/downloading images to/from AWS S3,
supporting both local file paths and S3 URIs.
"""

import os
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Union

from dotenv import load_dotenv
from PIL import Image

# Conditional boto3 import
try:
    import boto3

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    if not TYPE_CHECKING:
        boto3 = None  # type: ignore

# Load environment variables
load_dotenv()


def get_s3_client() -> "boto3.client":  # type: ignore
    """
    Create and return an S3 client using credentials from environment variables.

    Returns:
        boto3.client: Configured S3 client

    Raises:
        ValueError: If required AWS credentials are not found
        ImportError: If boto3 is not installed
    """
    if not HAS_BOTO3:
        raise ImportError(
            "boto3 is required for S3 operations. Install it with: pip install gemini-imagen[s3]"
        )

    access_key = os.getenv("GV_AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("GV_AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")

    if not access_key or not secret_key:
        raise ValueError(
            "AWS credentials not found. Set GV_AWS_ACCESS_KEY_ID and GV_AWS_SECRET_ACCESS_KEY "
            "environment variables."
        )

    return boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key)


def get_default_bucket() -> str:
    """
    Get the default S3 bucket name from environment variables.

    Returns:
        str: Bucket name

    Raises:
        ValueError: If bucket name is not configured
    """
    bucket = os.getenv("GV_AWS_STORAGE_BUCKET_NAME") or os.getenv("AWS_STORAGE_BUCKET_NAME")

    if not bucket:
        raise ValueError(
            "Default S3 bucket not configured. Set GV_AWS_STORAGE_BUCKET_NAME environment variable."
        )

    return bucket


def is_s3_uri(path: Union[str, Path]) -> bool:
    """
    Check if a path is an S3 URI.

    Args:
        path: Path or URI to check

    Returns:
        bool: True if path is an S3 URI (s3://...)
    """
    return str(path).startswith("s3://")


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """
    Parse an S3 URI into bucket and key components.

    Args:
        uri: S3 URI in format s3://bucket/key

    Returns:
        Tuple[str, str]: (bucket_name, object_key)

    Raises:
        ValueError: If URI format is invalid
    """
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI format: {uri}")

    # Remove s3:// prefix
    path = uri[5:]

    # Split into bucket and key
    parts = path.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI format: {uri}. Expected s3://bucket/key")

    bucket, key = parts
    return bucket, key


def get_http_url(bucket: str, key: str, region: str = "us-east-1") -> str:
    """
    Generate an HTTPS URL for an S3 object.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        region: AWS region (default: us-east-1)

    Returns:
        str: HTTPS URL that can be clicked in LangSmith
    """
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def upload_to_s3(
    local_path: Union[str, Path, Image.Image],
    s3_key: str,
    bucket: str | None = None,
    region: str = "us-east-1",
) -> tuple[str, str]:
    """
    Upload an image to S3 and return both S3 URI and HTTP URL.

    Args:
        local_path: Local file path or PIL Image object to upload
        s3_key: S3 object key (path within bucket)
        bucket: S3 bucket name (defaults to GV_AWS_STORAGE_BUCKET_NAME from env)
        region: AWS region (default: us-east-1)

    Returns:
        Tuple[str, str]: (s3_uri, http_url)

    Raises:
        ValueError: If bucket is not specified and no default is configured
        ClientError: If upload fails
    """
    if bucket is None:
        bucket = get_default_bucket()

    s3_client = get_s3_client()

    # Handle PIL Image objects
    if isinstance(local_path, Image.Image):
        # Convert PIL Image to bytes
        img_byte_arr = BytesIO()
        local_path.save(img_byte_arr, format="PNG")
        img_bytes = img_byte_arr.getvalue()

        # Upload from bytes
        s3_client.put_object(Bucket=bucket, Key=s3_key, Body=img_bytes, ContentType="image/png")
    else:
        # Upload from file path
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")

        # Determine content type from file extension
        content_type = "image/png" if local_path.suffix.lower() == ".png" else "image/jpeg"

        with local_path.open("rb") as f:
            s3_client.put_object(Bucket=bucket, Key=s3_key, Body=f, ContentType=content_type)

    # Generate URLs
    s3_uri = f"s3://{bucket}/{s3_key}"
    http_url = get_http_url(bucket, s3_key, region)

    return s3_uri, http_url


def download_from_s3(
    s3_uri: str, local_path: Union[str, Path] | None = None
) -> Union[Image.Image, str]:
    """
    Download an image from S3.

    Args:
        s3_uri: S3 URI in format s3://bucket/key
        local_path: Optional local path to save the file. If None, returns PIL Image object.

    Returns:
        Union[Image.Image, str]: PIL Image object if local_path is None, otherwise path to saved file

    Raises:
        ValueError: If S3 URI format is invalid
        ClientError: If download fails
    """
    bucket, key = parse_s3_uri(s3_uri)
    s3_client = get_s3_client()

    # Download to BytesIO buffer
    buffer = BytesIO()
    s3_client.download_fileobj(bucket, key, buffer)
    buffer.seek(0)

    # Load as PIL Image and convert to a new image to ensure it's fully in memory
    with Image.open(buffer) as img:
        # Convert to RGB to ensure compatibility and copy to memory
        image = img.convert("RGB").copy()

    if local_path is None:
        # Return PIL Image object
        return image
    else:
        # Save to local file
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(local_path)
        return str(local_path)


def load_image(path: Union[str, Path, Image.Image]) -> Image.Image:
    """
    Load an image from either a local path or S3 URI.

    This is a convenience function that handles both local files and S3 URIs transparently.

    Args:
        path: Local file path, S3 URI (s3://...), or PIL Image object

    Returns:
        Image.Image: PIL Image object

    Raises:
        ValueError: If path format is invalid
        FileNotFoundError: If local file doesn't exist
        ClientError: If S3 download fails
    """
    # If already a PIL Image, return as-is
    if isinstance(path, Image.Image):
        return path

    # If S3 URI, download from S3
    if is_s3_uri(path):
        return download_from_s3(path)

    # Otherwise, load from local path
    local_path = Path(path)
    if not local_path.exists():
        raise FileNotFoundError(f"File not found: {local_path}")

    return Image.open(local_path)


def save_image(
    image: Image.Image, output_location: Union[str, Path], region: str = "us-east-1"
) -> tuple[str, str | None, str | None]:
    """
    Save an image to either local filesystem or S3.

    Args:
        image: PIL Image object to save
        output_location: Local file path or S3 URI (s3://bucket/key)
        region: AWS region for S3 (default: us-east-1)

    Returns:
        Tuple[str, Optional[str], Optional[str]]: (local_path_or_s3_uri, s3_uri_or_none, http_url_or_none)
        - For local saves: (local_path, None, None)
        - For S3 saves: (s3_uri, s3_uri, http_url)

    Raises:
        ValueError: If output_location format is invalid
        ClientError: If S3 upload fails
    """
    # If S3 URI, upload to S3
    if is_s3_uri(output_location):
        bucket, key = parse_s3_uri(output_location)
        s3_uri, http_url = upload_to_s3(image, key, bucket, region)
        return s3_uri, s3_uri, http_url

    # Otherwise, save to local filesystem
    local_path = Path(output_location)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(local_path)
    return str(local_path), None, None
