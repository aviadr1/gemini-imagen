"""
Demonstrate Imagen model capabilities with advanced features.

This example shows how to use Imagen models (imagen-3, imagen-4) which support:
- Multiple image generation per call (number_of_images)
- Resolution control (image_size: 1K, 2K)
- Aspect ratio control (same as Gemini models)

Note: Imagen models may have different pricing and availability than Gemini models.
"""

import asyncio

from gemini_imagen import GeminiImageGenerator


async def main():
    """Demonstrate Imagen model advanced features."""
    # Initialize with Imagen model
    generator = GeminiImageGenerator(
        model_name="imagen-3.0-generate-001",  # or "imagen-4.0-generate-001"
        log_images=False,
    )

    print("\n" + "=" * 70)
    print("  IMAGEN MODEL ADVANCED FEATURES DEMO")
    print("=" * 70)

    # Example 1: Multiple different images per call
    print("\n1. Multiple Different Images (Variations)")
    print("-" * 70)
    print("  Generating 3 different variations in one API call")
    print("  Output: imagen_var1.png, imagen_var2.png, imagen_var3.png")

    result = await generator.generate(
        prompt="A futuristic robot in different poses",
        aspect_ratio="16:9",
        output_images=[
            ("Variation 1", "imagen_var1.png"),
            ("Variation 2", "imagen_var2.png"),
            ("Variation 3", "imagen_var3.png"),
        ],
    )

    print(f"\n  ✓ Generated {len(result.images)} different images")
    for i, img in enumerate(result.images):
        print(f"    {i + 1}. {img.size[0]}x{img.size[1]} - {result.image_labels[i]}")

    # Example 2: High resolution images (2K)
    print("\n\n2. High Resolution Images (2K)")
    print("-" * 70)
    print("  Generating 2K resolution image for print quality")
    print("  Output: imagen_2k_highres.png")

    result = await generator.generate(
        prompt="A detailed landscape with mountains and lakes",
        aspect_ratio="16:9",
        image_size="2K",  # Higher resolution
        output_images=["imagen_2k_highres.png"],
    )

    if result.image:
        print(f"  ✓ Generated 2K image: {result.image.size[0]}x{result.image.size[1]} pixels")
        total_pixels = result.image.size[0] * result.image.size[1]
        print(f"  Total pixels: {total_pixels:,}")

    # Example 3: Combining all features
    print("\n\n3. Combined Features: Multiple 2K Images")
    print("-" * 70)
    print("  Generating 2 different 2K images with custom aspect ratio")
    print("  Output: imagen_combined1.png, imagen_combined2.png")

    result = await generator.generate(
        prompt="Abstract art with vibrant colors",
        aspect_ratio=(21, 9),  # Ultra-widescreen
        image_size="2K",
        output_images=[
            ("Abstract Design 1", "imagen_combined1.png"),
            ("Abstract Design 2", "imagen_combined2.png"),
        ],
    )

    print(f"\n  ✓ Generated {len(result.images)} high-resolution images")
    for i, img in enumerate(result.images):
        print(
            f"    {i + 1}. {img.size[0]}x{img.size[1]} - {result.image_labels[i]} "
            f"({img.size[0] * img.size[1]:,} pixels)"
        )

    print("\n" + "=" * 70)
    print("Demo complete! Check the generated PNG files.")
    print("\nNote: Imagen models support advanced features:")
    print("  ✓ Multiple different images per call (not just duplicates)")
    print("  ✓ Resolution control (1K, 2K)")
    print("  ✓ Aspect ratio control (same as Gemini)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
