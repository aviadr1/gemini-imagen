# Safety Filtering in gemini-imagen

## Overview

Google Gemini's image generation models (gemini-2.5-flash-image) include built-in safety filtering that blocks inappropriate content. This document explains how safety filtering works and what information is available when content is blocked.

## How Safety Filtering Works

Gemini evaluates prompts and generated content for safety violations across multiple categories:
- Sexually explicit content
- Violent/dangerous content
- Harassment
- Hate speech

When content violates safety policies, Gemini returns a response with no generated content and a `finish_reason` indicating why.

## Response Structure

### Successful Generation

When generation succeeds, the response includes:

```python
{
  "candidates": [{
    "content": { "parts": [...] },  # Generated content
    "finish_reason": "STOP",        # types.FinishReason.STOP
    "index": 0
  }],
  "model_version": "gemini-2.5-flash-image",
  ...
}
```

**Note:** Even successful responses do NOT include `safety_ratings` or `prompt_feedback`.

### Blocked Content

When content is blocked, the response includes:

```python
{
  "candidates": [{
    "finish_reason": "NO_IMAGE",  # or "IMAGE_SAFETY"
    "index": 0
    # No 'content' field
    # No 'safety_ratings' field
  }],
  "model_version": "gemini-2.5-flash-image",
  ...
}
```

**Key observations:**
- ❌ No `safety_ratings` provided (even when blocked)
- ❌ No `prompt_feedback` provided
- ✅ `finish_reason` is the ONLY indicator of why content was blocked

## Finish Reason Values

The `finish_reason` field uses the `types.FinishReason` enum from `google.genai`.

**All possible values** (from SDK `types.FinishReason`):
- `FINISH_REASON_UNSPECIFIED` - Unspecified reason
- `STOP` - Generation completed successfully
- `MAX_TOKENS` - Hit token limit
- `SAFETY` - Blocked for general safety reasons
- `RECITATION` - Blocked for recitation
- `LANGUAGE` - Language not supported
- `OTHER` - Other unspecified reason
- `BLOCKLIST` - Hit blocklist
- `PROHIBITED_CONTENT` - Blocked for prohibited content
- `SPII` - Sensitive personal information detected
- `MALFORMED_FUNCTION_CALL` - Function call was malformed
- `IMAGE_SAFETY` - Blocked for image-specific safety reasons
- `UNEXPECTED_TOOL_CALL` - Unexpected tool call
- `IMAGE_PROHIBITED_CONTENT` - Blocked for image-specific prohibited content
- `NO_IMAGE` - No image could be generated

**Common values for image generation:**
- `STOP` - Successful generation
- `NO_IMAGE` - No image generated (often safety-related)
- `IMAGE_SAFETY` - Blocked for image safety
- `IMAGE_PROHIBITED_CONTENT` - Blocked prohibited image content

## What gemini-imagen Logs

When content is blocked, `gemini-imagen` automatically:

1. **Extracts safety information:**
   - `finish_reason` (actual `types.FinishReason` enum)
   - `finish_message` (if provided)
   - Full response JSON

2. **Logs to LangSmith** (if `log_images=True`):
   - `safety_finish_reason` - The actual finish reason enum
   - `safety_finish_message` - Message if provided

3. **Raises ValueError with details:**
   ```python
   ValueError: No content parts in response. Finish reason: IMAGE_SAFETY

   Full response:
   {...}
   ```

## Example: Handling Blocked Content

```python
from gemini_imagen import GeminiImageGenerator
from google.genai import types

generator = GeminiImageGenerator(log_images=True)

try:
    result = await generator.generate(
        prompt="inappropriate content",
        output_images=["output.png"]
    )
except ValueError as e:
    error_msg = str(e)

    # Check the finish reason in the error message
    if "IMAGE_SAFETY" in error_msg:
        print("Content blocked for image safety")
    elif "NO_IMAGE" in error_msg:
        print("No image could be generated")

    # Full response JSON is included in error for debugging
    print(f"Error details: {error_msg}")
```

## Configuring Safety Settings

You can customize safety filtering thresholds to control which content is blocked. This is useful when you need more or less restrictive filtering for your use case.

### CLI Usage

#### Setting Global Defaults

Set a global safety preset that applies to all generations:

```bash
# Relaxed filtering (only blocks high-probability harmful content)
imagen config set safety_settings relaxed

# Strict filtering (blocks low, medium, and high probability)
imagen config set safety_settings strict

# Default filtering (blocks medium and high probability)
imagen config set safety_settings default

# Minimal filtering
imagen config set safety_settings none
```

#### Per-Generation Override

Override safety settings for a specific generation:

```bash
# Use a preset for all categories
imagen generate "prompt" -o output.png --safety-setting preset:relaxed

# Set specific category threshold
imagen generate "prompt" -o output.png --safety-setting SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH

# Combine multiple settings
imagen generate "prompt" -o output.png \
  --safety-setting SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH \
  --safety-setting DANGEROUS_CONTENT:BLOCK_LOW_AND_ABOVE
```

### Available Safety Categories

- `HARM_CATEGORY_SEXUALLY_EXPLICIT` - Sexually explicit content
- `HARM_CATEGORY_DANGEROUS_CONTENT` - Violent or dangerous content
- `HARM_CATEGORY_HARASSMENT` - Harassment
- `HARM_CATEGORY_HATE_SPEECH` - Hate speech
- `HARM_CATEGORY_CIVIC_INTEGRITY` - Civic integrity violations

### Safety Thresholds

- `BLOCK_NONE` - Disable blocking for this category
- `BLOCK_ONLY_HIGH` - Relaxed, only block high-probability harmful content
- `BLOCK_MEDIUM_AND_ABOVE` - Default, block medium and high probability
- `BLOCK_LOW_AND_ABOVE` - Strict, block low, medium, and high probability

### Example: Relaxed Settings

```python
from gemini_imagen import GeminiImageGenerator, SafetySetting, HarmCategory, HarmBlockThreshold

generator = GeminiImageGenerator(log_images=True)

# Configure relaxed settings for artistic content
relaxed_settings = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH
    )
]

try:
    result = await generator.generate(
        prompt="A tasteful artistic nude statue, black and white photograph",
        output_images=["output.png"],
        safety_settings=relaxed_settings
    )
except ValueError as e:
    print(f"Content blocked: {e}")
```

### Example: Strict Settings

```python
from gemini_imagen import GeminiImageGenerator, SafetySetting, HarmCategory, HarmBlockThreshold

generator = GeminiImageGenerator(log_images=True)

# Configure strict settings for family-friendly content
strict_settings = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
    )
]

result = await generator.generate(
    prompt="A peaceful mountain landscape",
    output_images=["output.png"],
    safety_settings=strict_settings
)
```

### Default Behavior

When `safety_settings=None` (the default), Gemini uses its built-in default thresholds.

To have precise control over safety filtering, explicitly configure thresholds:
- Use `BLOCK_LOW_AND_ABOVE` for strict, family-friendly filtering
- Use `BLOCK_ONLY_HIGH` for relaxed, artistic content filtering

### Important Notes

1. **Safety settings are optional**: Omit `safety_settings` to use Gemini's defaults
2. **Per-category configuration**: You can set different thresholds for different categories
3. **Model behavior may vary**: Even with relaxed settings, the model may still block content based on its internal policies
4. **Cannot completely disable safety**: `BLOCK_NONE` reduces blocking but doesn't guarantee all content will be allowed

## Testing Safety Filtering

See integration tests:
- `tests/test_e2e_integration.py::TestSafetyFiltering` - Tests for safety blocking behavior
- `tests/test_e2e_integration.py::TestSafetySettings` - Tests for configurable safety settings

Example prompts that trigger blocking:
- "nude picture of [person]" → `NO_IMAGE` or `IMAGE_SAFETY`
- "explicit sexual content" → `NO_IMAGE`
- "violent gore scene" → `NO_IMAGE`

The `TestSafetySettings` tests demonstrate:
- Relaxed settings (`BLOCK_ONLY_HIGH`) with borderline content
- Strict settings (`BLOCK_LOW_AND_ABOVE`) blocking borderline content
- Default settings behavior (`None`)
- Configuring multiple safety categories with different thresholds

The tests use carefully crafted borderline prompts to validate threshold differences.

## SDK Type Reference

All safety-related types come from `google.genai.types`:

- `FinishReason` - Enum of completion/blocking reasons
- `BlockedReason` - Enum of block reasons (for prompt_feedback, rarely used)
- `HarmCategory` - Enum of harm categories (not provided in responses)
- `SafetyRating` - Safety rating object (not provided in responses)

## Important Notes

1. **No detailed safety ratings**: Gemini does not provide `safety_ratings`, `HarmCategory` scores, or `HarmProbability` values in image generation responses - only the `finish_reason` enum.

2. **Use actual SDK enums**: `gemini-imagen` stores actual `types.FinishReason` enum values (not strings) for type safety and forward compatibility.

3. **LangSmith serialization**: LangSmith automatically serializes SDK enums to strings for display.

4. **Error handling**: Always check `finish_reason` to determine why content was blocked.
