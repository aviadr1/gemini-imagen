"""
Basic text-to-image generation example.

This example shows the simplest use case: generating an image from a text prompt.
"""

import asyncio

from dotenv import load_dotenv

from gemini_imagen import GeminiImageGenerator

# Load environment variables from .env file
load_dotenv()


async def main():
    # Initialize the generator
    generator = GeminiImageGenerator()

    # Generate an image from a text prompt
    result = await generator.generate(
        prompt="A serene Japanese garden with cherry blossoms in full bloom, koi pond, stone lanterns",
        output_images=["garden.png"],
    )

    print("✓ Image generated successfully!")
    print(f"  Saved to: {result.image_location}")
    print(f"  Size: {result.image.size}")


if __name__ == "__main__":
    asyncio.run(main())
