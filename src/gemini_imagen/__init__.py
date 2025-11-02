"""
Imagen - Gemini Image Generation with S3 and LangSmith Integration
===================================================================

This package provides a unified API for Google Gemini image generation with
full S3 support and LangSmith tracing.

Main API:
    GeminiImageGenerator - Main class with unified generate() method

S3 Utilities:
    load_image - Load images from local paths or S3 URIs
    save_image - Save images to local paths or S3 URIs
    upload_to_s3 - Upload images to S3
    download_from_s3 - Download images from S3
    is_s3_uri - Check if a path is an S3 URI
    parse_s3_uri - Parse S3 URI into bucket and key
    get_http_url - Generate HTTP URL from S3 bucket and key

Example:
    from imagen import GeminiImageGenerator

    generator = GeminiImageGenerator(log_images=True)

    # Unified API - does everything
    result = generator.generate(
        prompt="A sunset over mountains",
        input_images=["s3://bucket/input.png"],
        output_image_location="s3://bucket/output.png",
        tags=["demo"]
    )

    print(result.image_s3_uri)     # s3://bucket/output.png
    print(result.image_http_url)   # https://bucket.s3...
"""

from .gemini_image_wrapper import (
    GeminiImageGenerator,
    GenerationResult,
    HarmBlockThreshold,
    HarmCategory,
    ImageType,
    ResponseModality,
    SafetySetting,
)
from .s3_utils import (
    download_from_http,
    download_from_s3,
    get_default_bucket,
    get_http_url,
    is_http_url,
    is_s3_uri,
    load_image,
    parse_s3_uri,
    save_image,
    upload_to_s3,
)

__all__ = [
    "GeminiImageGenerator",
    "GenerationResult",
    "HarmBlockThreshold",
    "HarmCategory",
    "ImageType",
    "ResponseModality",
    "SafetySetting",
    "download_from_http",
    "download_from_s3",
    "get_default_bucket",
    "get_http_url",
    "is_http_url",
    "is_s3_uri",
    "load_image",
    "parse_s3_uri",
    "save_image",
    "upload_to_s3",
]

__version__ = "0.1.0"
