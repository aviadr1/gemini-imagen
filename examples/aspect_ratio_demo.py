"""
Demonstrate aspect ratio and image size control.

This example shows how to generate images with different aspect ratios
and resolutions using both preset and custom ratios.
"""

import asyncio

from gemini_imagen import GeminiImageGenerator


async def main():
    """Generate images with different aspect ratios and sizes."""
    generator = GeminiImageGenerator(log_images=False)

    print("\n" + "=" * 70)
    print("  ASPECT RATIO & RESOLUTION DEMO")
    print("=" * 70)

    # Example 1: Preset aspect ratios
    print("\n1. Preset Aspect Ratios")
    print("-" * 70)

    presets = [
        ("1:1", "Square (default)"),
        ("16:9", "Widescreen"),
        ("9:16", "Portrait/Vertical"),
        ("4:3", "Fullscreen"),
        ("3:4", "Portrait fullscreen"),
    ]

    for ratio, description in presets:
        print(f"\n  {ratio:5s} - {description}")
        print(f"  Output: output_{ratio.replace(':', 'x')}.png")

        result = await generator.generate(
            prompt="A serene mountain landscape at sunset",
            aspect_ratio=ratio,
            output_images=[f"output_{ratio.replace(':', 'x')}.png"],
        )

        if result.image:
            print(f"  ✓ Generated: {result.image.size[0]}x{result.image.size[1]}")

    # Example 2: Custom aspect ratio
    print("\n\n2. Custom Aspect Ratio")
    print("-" * 70)
    print("  Using tuple (21, 9) for ultra-widescreen")
    print("  Output: output_21x9.png")

    result = await generator.generate(
        prompt="A panoramic city skyline at night",
        aspect_ratio=(21, 9),  # Custom ultra-widescreen
        output_images=["output_21x9.png"],
    )

    if result.image:
        print(f"  ✓ Generated: {result.image.size[0]}x{result.image.size[1]}")

    # Example 3: Higher resolution
    print("\n\n3. Higher Resolution (2K)")
    print("-" * 70)
    print("  Using image_size='2K' for higher quality")
    print("  Output: output_2k.png")
    print("  Note: 2K is only supported on Standard/Ultra models")

    result = await generator.generate(
        prompt="A detailed close-up of a colorful butterfly",
        aspect_ratio="1:1",
        image_size="2K",
        output_images=["output_2k.png"],
    )

    if result.image:
        print(f"  ✓ Generated: {result.image.size[0]}x{result.image.size[1]}")

    # Example 4: Multiple images with aspect ratio
    print("\n\n4. Multiple Images (Variations)")
    print("-" * 70)
    print("  Generating 3 variations in 16:9 aspect ratio")
    print("  Output: variation_1.png, variation_2.png, variation_3.png")

    result = await generator.generate(
        prompt="A futuristic city with flying cars",
        aspect_ratio="16:9",
        output_images=[
            ("Variation 1", "variation_1.png"),
            ("Variation 2", "variation_2.png"),
            ("Variation 3", "variation_3.png"),
        ],
    )

    print(f"  ✓ Generated {len(result.images)} images")
    for i, img in enumerate(result.images):
        print(f"    {i + 1}. {img.size[0]}x{img.size[1]} - {result.image_labels[i]}")

    print("\n" + "=" * 70)
    print("Demo complete! Check the generated PNG files.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
