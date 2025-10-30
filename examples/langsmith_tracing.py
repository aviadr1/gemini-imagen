"""
LangSmith tracing example.

This example shows how to enable LangSmith tracing for observability.
"""

import os
from dotenv import load_dotenv
from gemini_imagen import GeminiImageGenerator

load_dotenv()

# Enable LangSmith tracing
os.environ["LANGSMITH_TRACING"] = "true"
# Make sure you have LANGSMITH_API_KEY in your .env

# Enable image logging to LangSmith
generator = GeminiImageGenerator(log_images=True)

# Generate with metadata and tags
result = generator.generate(
    prompt="A magical forest with glowing mushrooms and fairy lights",
    output_images=["magical_forest.png"],
    metadata={
        "user_id": "demo_user",
        "session": "example_run"
    },
    tags=["example", "demo", "magical-forest"]
)

print(f"✓ Image generated with LangSmith tracing!")
print(f"  Saved to: {result.image_location}")
print(f"\n📊 Check your trace at: https://smith.langchain.com/")
