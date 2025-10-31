"""
Labeled input images example.

This example shows how to label input images so you can reference them
by name in your prompts for better control.
"""

import asyncio

from dotenv import load_dotenv

from gemini_imagen import GeminiImageGenerator

load_dotenv()


async def main():
    generator = GeminiImageGenerator()

    # Use labeled input images
    result = await generator.generate(
        prompt="Blend the artistic style from Photo A with the composition from Photo B",
        input_images=[
            ("Photo A (style reference):", "garden.png"),
            ("Photo B (composition reference):", "garden.png"),  # Using same for demo
        ],
        output_images=["blended.png"],
    )

    print("✓ Blended image created!")
    print(f"  Saved to: {result.image_location}")


if __name__ == "__main__":
    asyncio.run(main())
