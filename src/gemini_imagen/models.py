"""
Pydantic models for gemini-imagen.

Shared between the library and CLI to ensure consistent parameter handling.
"""

from typing import Any

from google.genai import types
from pydantic import BaseModel, ConfigDict, Field

# Type aliases for better documentation
ImageSource = str | tuple[str, str]  # path or (label, path)
OutputImageSpec = str  # path


class GenerateParams(BaseModel):
    """
    Parameters for the generate() method.

    This model is shared between the CLI and library to ensure consistency
    and enable clean LangSmith traces using model_dump(exclude_none=True).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Required
    prompt: str = Field(description="User prompt text")

    # Image generation configuration
    system_prompt: str | None = Field(
        default=None, description="Optional system prompt for the model"
    )
    input_images: list[ImageSource] | None = Field(default=None, description="List of input images")
    temperature: float | None = Field(default=None, description="Sampling temperature (0.0 to 1.0)")
    aspect_ratio: str | tuple[int, int] | None = Field(
        default=None, description="Image aspect ratio"
    )
    safety_settings: list[types.SafetySetting] | None = Field(
        default=None, description="Safety configuration"
    )

    # Output configuration
    output_images: list[OutputImageSpec] | None = Field(
        default=None, description="Output image paths/URIs"
    )
    output_text: bool = Field(default=False, description="Whether to also request text output")

    # LangSmith configuration
    run_name: str | None = Field(default=None, description="Custom name for the LangSmith run")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata for LangSmith"
    )
    tags: list[str] | None = Field(default=None, description="Tags for LangSmith tracing")
