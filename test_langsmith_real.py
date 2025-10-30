"""
Real end-to-end test with LangSmith to verify S3 URL logging.

This script generates an image with S3 output and verifies that the
S3 URLs are actually logged to LangSmith.
"""

import os
from datetime import datetime

from dotenv import load_dotenv

from gemini_imagen import GeminiImageGenerator

load_dotenv()

# Enable LangSmith tracing
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "gemini-imagen"

aws_bucket = os.getenv("GV_AWS_STORAGE_BUCKET_NAME")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

print("=" * 70)
print("LangSmith S3 Logging Verification Test")
print("=" * 70)

# Create generator with logging enabled
generator = GeminiImageGenerator(log_images=True)

print("\nGenerator config:")
print(f"  log_images: {generator.log_images}")
print(f"  LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")

# Test 1: Generate image with S3 output
print("\n" + "-" * 70)
print("Test 1: Text-to-Image with S3 output")
print("-" * 70)

s3_output_path = f"s3://{aws_bucket}/langsmith_test/test_{timestamp}.png"
print(f"Output path: {s3_output_path}")

result = generator.generate(
    prompt="A simple red circle on white background",
    output_images=[("Test Output", s3_output_path)],
    run_name="langsmith_real_test_image_generation",
    tags=["langsmith-test", "s3-logging"],
)

print("\n✓ Image generated!")
print(f"  S3 URI: {result.image_s3_uri}")
print(f"  HTTP URL: {result.image_http_url}")

# Test 2: Image analysis with S3 input
print("\n" + "-" * 70)
print("Test 2: Image Analysis with S3 input")
print("-" * 70)

print(f"Input from: {result.image_s3_uri}")

result2 = generator.generate(
    prompt="Describe this image in one sentence",
    input_images=[("Previous image:", result.image_s3_uri)],
    output_text=True,
    run_name="langsmith_real_test_image_analysis",
    tags=["langsmith-test", "s3-input"],
)

print("\n✓ Analysis complete!")
print(f"  Response: {result2.text}")

print("\n" + "=" * 70)
print("✅ Tests Complete!")
print("=" * 70)
print("\n📊 Check LangSmith project 'gemini-imagen' for:")
print("  1. Run 'langsmith_real_test_image_generation' with tags: langsmith-test, s3-logging")
print("     - Should have output_image_0_s3_uri in outputs")
print("     - Should have output_image_0_http_url in outputs")
print()
print("  2. Run 'langsmith_real_test_image_analysis' with tags: langsmith-test, s3-input")
print("     - Should have input_image_0_s3_uri in inputs")
print("     - Should have input_image_0_http_url in inputs")
print()
print("🔗 LangSmith URL: https://smith.langchain.com/o/YOURORG/projects/p/gemini-imagen")
print()
print("If you don't see S3 URLs in the traces, the logging is NOT working.")
