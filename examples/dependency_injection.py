"""Dependency injection example.

This example shows how to pass credentials directly to the GeminiImageGenerator
constructor instead of relying on environment variables. This is useful for:
- Testing with different credentials
- Applications that manage credentials programmatically
- Multi-tenant applications
"""

import asyncio

from gemini_imagen import GeminiImageGenerator


async def main():
    # Example 1: Passing all credentials explicitly
    generator = GeminiImageGenerator(
        api_key="your-google-api-key-here",
        aws_access_key_id="your-aws-access-key-id",
        aws_secret_access_key="your-aws-secret-access-key",
        aws_storage_bucket_name="your-bucket-name",
        aws_region="us-east-1",
        log_images=True,
    )

    # Example 2: Partial dependency injection (mix with environment variables)
    # Only override specific credentials, others will fall back to env vars
    _generator2 = GeminiImageGenerator(
        api_key="your-google-api-key-here",  # Override Google API key
        # AWS credentials will be read from environment variables:
        # GV_AWS_ACCESS_KEY_ID, GV_AWS_SECRET_ACCESS_KEY, GV_AWS_STORAGE_BUCKET_NAME
    )

    # Example 3: Using environment variables (default behavior)
    # All credentials read from environment variables:
    # - GOOGLE_API_KEY or GEMINI_API_KEY
    # - GV_AWS_ACCESS_KEY_ID or AWS_ACCESS_KEY_ID
    # - GV_AWS_SECRET_ACCESS_KEY or AWS_SECRET_ACCESS_KEY
    # - GV_AWS_STORAGE_BUCKET_NAME or AWS_STORAGE_BUCKET_NAME
    _generator3 = GeminiImageGenerator()

    # Generate an image
    result = await generator.generate(
        prompt="A serene mountain landscape at sunrise",
        output_images=["mountain_sunrise.png"],
    )

    print("✓ Image generated!")
    print(f"  Location: {result.image_location}")


if __name__ == "__main__":
    asyncio.run(main())
