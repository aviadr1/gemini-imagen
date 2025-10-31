"""
S3 integration example.

This example shows how to use S3 for both input and output images.
Requires AWS credentials to be configured.
"""

import asyncio
import os

from dotenv import load_dotenv

from gemini_imagen import GeminiImageGenerator

load_dotenv()


async def main():
    # You need these environment variables:
    # GV_AWS_ACCESS_KEY_ID
    # GV_AWS_SECRET_ACCESS_KEY
    # GV_AWS_STORAGE_BUCKET_NAME

    aws_bucket = os.getenv("GV_AWS_STORAGE_BUCKET_NAME")

    if not aws_bucket:
        print("⚠️  AWS bucket not configured. Set GV_AWS_STORAGE_BUCKET_NAME in .env")
        exit(1)

    generator = GeminiImageGenerator(log_images=True)

    # Generate image directly to S3
    result = await generator.generate(
        prompt="A futuristic cityscape at sunset with flying cars",
        output_images=[f"s3://{aws_bucket}/examples/cityscape.png"],
    )

    print("✓ Image uploaded to S3!")
    print(f"  S3 URI: {result.image_s3_uri}")
    print(f"  HTTP URL: {result.image_http_url}")

    # Edit an image from S3 and save back to S3
    result2 = await generator.generate(
        prompt="Transform this into a cyberpunk style with neon lights",
        input_images=[result.image_s3_uri],  # Use the S3 URI as input
        output_images=[f"s3://{aws_bucket}/examples/cityscape_cyberpunk.png"],
    )

    print("\n✓ Edited image uploaded to S3!")
    print(f"  S3 URI: {result2.image_s3_uri}")
    print(f"  HTTP URL: {result2.image_http_url}")


if __name__ == "__main__":
    asyncio.run(main())
