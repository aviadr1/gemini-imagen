"""
S3 Utility Functions for Image Storage
======================================

This module provides async utilities for uploading/downloading images to/from AWS S3,
supporting both local file paths, S3 URIs, and HTTP(S) URLs.
"""

import asyncio
import os
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

import aiofiles
import aiohttp
from dotenv import load_dotenv
from PIL import Image

# Conditional aioboto3 import
if TYPE_CHECKING:
    import aioboto3

    HAS_AIOBOTO3 = True
else:
    try:
        import aioboto3

        HAS_AIOBOTO3 = True
    except ImportError:
        HAS_AIOBOTO3 = False
        aioboto3 = None  # type: ignore[assignment]

# Load environment variables
load_dotenv()


def get_async_s3_session(
    access_key_id: str | None = None, secret_access_key: str | None = None
) -> Any:  # aioboto3.Session
    """
    Create and return an aioboto3 session for async S3 operations.

    Args:
        access_key_id: AWS access key ID (defaults to environment variables)
        secret_access_key: AWS secret access key (defaults to environment variables)

    Returns:
        aioboto3.Session: Configured aioboto3 session

    Raises:
        ValueError: If required AWS credentials are not found
        ImportError: If aioboto3 is not installed
    """
    if not HAS_AIOBOTO3:
        raise ImportError(
            "aioboto3 is required for S3 operations. Install it with: pip install gemini-imagen[s3]"
        )

    access_key = (
        access_key_id or os.getenv("GV_AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
    )
    secret_key = (
        secret_access_key
        or os.getenv("GV_AWS_SECRET_ACCESS_KEY")
        or os.getenv("AWS_SECRET_ACCESS_KEY")
    )

    if not access_key or not secret_key:
        raise ValueError(
            "AWS credentials not found. Set GV_AWS_ACCESS_KEY_ID and GV_AWS_SECRET_ACCESS_KEY "
            "environment variables, or pass access_key_id and secret_access_key parameters."
        )

    return aioboto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key)  # type: ignore[union-attr]


def get_default_bucket(bucket_name: str | None = None) -> str:
    """
    Get the default S3 bucket name from parameter or environment variables.

    Args:
        bucket_name: S3 bucket name (defaults to environment variables)

    Returns:
        str: Bucket name

    Raises:
        ValueError: If bucket name is not configured
    """
    bucket = (
        bucket_name
        or os.getenv("GV_AWS_STORAGE_BUCKET_NAME")
        or os.getenv("AWS_STORAGE_BUCKET_NAME")
    )

    if not bucket:
        raise ValueError(
            "Default S3 bucket not configured. Set GV_AWS_STORAGE_BUCKET_NAME environment variable, "
            "or pass bucket_name parameter."
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


def is_http_url(path: Union[str, Path]) -> bool:
    """
    Check if a path is an HTTP or HTTPS URL.

    Args:
        path: Path or URI to check

    Returns:
        bool: True if path is an HTTP(S) URL
    """
    path_str = str(path)
    return path_str.startswith("http://") or path_str.startswith("https://")


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


async def upload_to_s3(
    local_path: Union[str, Path, Image.Image],
    s3_key: str,
    bucket: str | None = None,
    region: str = "us-east-1",
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
) -> tuple[str, str]:
    """
    Upload an image to S3 and return both S3 URI and HTTP URL.

    Args:
        local_path: Local file path or PIL Image object to upload
        s3_key: S3 object key (path within bucket)
        bucket: S3 bucket name (defaults to GV_AWS_STORAGE_BUCKET_NAME from env)
        region: AWS region (default: us-east-1)
        access_key_id: AWS access key ID (defaults to environment variables)
        secret_access_key: AWS secret access key (defaults to environment variables)

    Returns:
        Tuple[str, str]: (s3_uri, http_url)

    Raises:
        ValueError: If bucket is not specified and no default is configured
        ClientError: If upload fails
    """
    if bucket is None:
        bucket = get_default_bucket()

    session = get_async_s3_session(access_key_id=access_key_id, secret_access_key=secret_access_key)

    # Handle PIL Image objects
    if isinstance(local_path, Image.Image):
        # Convert PIL Image to bytes (run in executor since PIL is sync)
        loop = asyncio.get_event_loop()
        img_byte_arr = BytesIO()
        await loop.run_in_executor(None, local_path.save, img_byte_arr, "PNG")
        img_bytes = img_byte_arr.getvalue()

        # Upload from bytes
        async with session.client("s3") as s3_client:  # type: ignore[union-attr]
            await s3_client.put_object(
                Bucket=bucket, Key=s3_key, Body=img_bytes, ContentType="image/png"
            )  # type: ignore[union-attr]
    else:
        # Upload from file path
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")

        # Determine content type from file extension
        content_type = "image/png" if local_path.suffix.lower() == ".png" else "image/jpeg"

        async with aiofiles.open(local_path, "rb") as f:
            file_data = await f.read()
            async with session.client("s3") as s3_client:  # type: ignore[union-attr]
                await s3_client.put_object(
                    Bucket=bucket, Key=s3_key, Body=file_data, ContentType=content_type
                )  # type: ignore[union-attr]

    # Generate URLs
    s3_uri = f"s3://{bucket}/{s3_key}"
    http_url = get_http_url(bucket, s3_key, region)

    return s3_uri, http_url


async def download_from_http(url: str) -> Image.Image:
    """
    Download an image from an HTTP(S) URL.

    Args:
        url: HTTP(S) URL to download from

    Returns:
        Image.Image: PIL Image object

    Raises:
        aiohttp.ClientError: If download fails
    """
    async with aiohttp.ClientSession() as session, session.get(url) as response:
        response.raise_for_status()
        image_data = await response.read()

    # Load as PIL Image in executor since PIL is sync
    buffer = BytesIO(image_data)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: Image.open(buffer).convert("RGB").copy())


async def download_from_s3(
    s3_uri: str,
    local_path: Union[str, Path] | None = None,
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
) -> Union[Image.Image, str]:
    """
    Download an image from S3.

    Args:
        s3_uri: S3 URI in format s3://bucket/key
        local_path: Optional local path to save the file. If None, returns PIL Image object.
        access_key_id: AWS access key ID (defaults to environment variables)
        secret_access_key: AWS secret access key (defaults to environment variables)

    Returns:
        Union[Image.Image, str]: PIL Image object if local_path is None, otherwise path to saved file

    Raises:
        ValueError: If S3 URI format is invalid
        ClientError: If download fails
    """
    bucket, key = parse_s3_uri(s3_uri)
    session = get_async_s3_session(access_key_id=access_key_id, secret_access_key=secret_access_key)

    # Download to BytesIO buffer
    buffer = BytesIO()
    async with session.client("s3") as s3_client:  # type: ignore[union-attr]
        response = await s3_client.get_object(Bucket=bucket, Key=key)  # type: ignore[union-attr]
        async with response["Body"] as stream:  # type: ignore[union-attr]
            buffer.write(await stream.read())  # type: ignore[union-attr]

    buffer.seek(0)

    # Load as PIL Image and convert to a new image to ensure it's fully in memory
    # Run in executor since PIL is sync
    loop = asyncio.get_event_loop()
    image = await loop.run_in_executor(None, lambda: Image.open(buffer).convert("RGB").copy())

    if local_path is None:
        # Return PIL Image object
        return image
    else:
        # Save to local file asynchronously
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Save image in executor since PIL is sync
        await loop.run_in_executor(None, image.save, local_path)
        return str(local_path)


async def load_image(
    path: Union[str, Path, Image.Image],
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
) -> Image.Image:
    """
    Load an image from a local path, S3 URI, HTTP(S) URL, or PIL Image.

    This is a convenience function that handles all image sources transparently.

    Args:
        path: Local file path, S3 URI (s3://...), HTTP(S) URL, or PIL Image object
        access_key_id: AWS access key ID (defaults to environment variables)
        secret_access_key: AWS secret access key (defaults to environment variables)

    Returns:
        Image.Image: PIL Image object

    Raises:
        ValueError: If path format is invalid
        FileNotFoundError: If local file doesn't exist
        ClientError: If S3 or HTTP download fails
    """
    # If already a PIL Image, return as-is
    if isinstance(path, Image.Image):
        return path

    # If HTTP(S) URL, download from web
    if is_http_url(path):
        return await download_from_http(str(path))

    # If S3 URI, download from S3
    if is_s3_uri(path):
        result = await download_from_s3(
            str(path), access_key_id=access_key_id, secret_access_key=secret_access_key
        )
        if isinstance(result, str):
            # Shouldn't happen when local_path is None, but satisfy mypy
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, Image.open, result)
        return result

    # Otherwise, load from local path (run in executor since PIL is sync)
    local_path = Path(path)
    if not local_path.exists():
        raise FileNotFoundError(f"File not found: {local_path}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, Image.open, local_path)


async def save_image(
    image: Image.Image,
    output_location: Union[str, Path],
    region: str = "us-east-1",
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
) -> tuple[str, str | None, str | None]:
    """
    Save an image to either local filesystem or S3.

    Args:
        image: PIL Image object to save
        output_location: Local file path or S3 URI (s3://bucket/key)
        region: AWS region for S3 (default: us-east-1)
        access_key_id: AWS access key ID (defaults to environment variables)
        secret_access_key: AWS secret access key (defaults to environment variables)

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
        bucket, key = parse_s3_uri(str(output_location))
        s3_uri, http_url = await upload_to_s3(
            image,
            key,
            bucket,
            region,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
        return s3_uri, s3_uri, http_url

    # Otherwise, save to local filesystem (run in executor since PIL is sync)
    local_path = Path(output_location).resolve()
    local_path.parent.mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, image.save, local_path)
    return str(local_path), None, None
