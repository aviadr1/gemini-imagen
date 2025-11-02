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

The `finish_reason` field uses the `types.FinishReason` enum from `google.genai`:

**Normal completion:**
- `STOP` - Generation completed successfully

**Safety-related blocking:**
- `SAFETY` - Blocked for general safety reasons
- `IMAGE_SAFETY` - Blocked for image-specific safety reasons
- `NO_IMAGE` - No image could be generated (often safety-related)
- `PROHIBITED_CONTENT` - Blocked for prohibited content
- `IMAGE_PROHIBITED_CONTENT` - Blocked for image-specific prohibited content
- `JAILBREAK` - Detected jailbreak attempt

**Other blocking reasons:**
- `MAX_TOKENS` - Hit token limit
- `RECITATION` - Blocked for recitation
- `BLOCKLIST` - Hit blocklist
- `SPII` - Sensitive personal information detected
- `LANGUAGE` - Language not supported
- `OTHER` - Other unspecified reason

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

## Testing Safety Filtering

See `tests/test_e2e_integration.py::TestSafetyFiltering` for integration tests.

Example prompts that trigger blocking:
- "nude picture of [person]" → `NO_IMAGE` or `IMAGE_SAFETY`
- "explicit sexual content" → `NO_IMAGE`
- "violent gore scene" → `NO_IMAGE`

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
