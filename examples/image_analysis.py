"""
Image analysis example.

This example shows how to analyze an existing image and get a text description.
"""

import os
from dotenv import load_dotenv
from gemini_imagen import GeminiImageGenerator

load_dotenv()

generator = GeminiImageGenerator()

# Analyze an image
result = generator.generate(
    prompt="Analyze this image in detail. Describe the main objects, colors, mood, and setting.",
    input_images=["garden.png"],  # Use the image from basic_generation.py
    output_text=True
)

print("Image Analysis:")
print("=" * 70)
print(result.text)
