"""
HTTP(S) URL input example.

This example shows how to use HTTP(S) URLs as input images.
"""

import asyncio

from dotenv import load_dotenv

from gemini_imagen import GeminiImageGenerator

load_dotenv()


async def main():
    generator = GeminiImageGenerator(log_images=True)

    # Example HTTP URL (you can use any publicly accessible image URL)
    http_image_url = (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg"
    )

    # Use HTTP URL as input image
    result = await generator.generate(
        prompt="Describe this image in detail",
        input_images=[http_image_url],
        output_text=True,
    )

    print("Image Analysis from HTTP URL:")
    print("=" * 70)
    print(result.text)

    # You can also use labeled HTTP inputs
    result2 = await generator.generate(
        prompt="Transform this image into a watercolor painting style",
        input_images=[("Original image from web:", http_image_url)],
        output_images=["watercolor_cat.png"],
    )

    print("\n✓ Watercolor image generated!")
    print(f"  Saved to: {result2.image_location}")


if __name__ == "__main__":
    asyncio.run(main())
