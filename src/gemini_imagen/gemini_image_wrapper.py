"""
Gemini Image Generation with S3 and LangSmith Integration
==========================================================

This module provides a clean, unified API for Google Gemini image generation
with full S3 support, structured output, and LangSmith tracing.

Main API:
    GeminiImageGenerator.generate() - Unified method supporting:
        - Labeled input images
        - Multiple output images
        - Structured output (Pydantic models)
        - Text, image, or combined outputs

Usage:
    from imagen import GeminiImageGenerator
    from pydantic import BaseModel

    generator = GeminiImageGenerator(log_images=True)

    # Basic text-to-image
    result = generator.generate(
        prompt="A sunset over mountains",
        output_images=["s3://bucket/output.png"]
    )

    # Labeled input images
    result = generator.generate(
        prompt="Blend these styles",
        input_images=[
            ("Photo A:", "s3://bucket/input1.png"),
            ("Photo B:", "s3://bucket/input2.png")
        ],
        output_images=["s3://bucket/blended.png"]
    )

    # Structured output
    class Analysis(BaseModel):
        objects: list[str]
        colors: list[str]

    result = generator.generate(
        prompt="Analyze this image",
        input_images=["image.png"],
        output_schema=Analysis
    )
    print(result.structured.objects)
"""

import os
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

import google.generativeai as genai
from dotenv import load_dotenv
from google.generativeai.types import GenerateContentResponse
from langsmith import get_current_run_tree, traceable
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from .s3_utils import (
    get_http_url,
    is_s3_uri,
    load_image,
    parse_s3_uri,
    save_image,
)

if TYPE_CHECKING:
    from langsmith.run_trees import RunTree

# Load environment variables
load_dotenv()


# Enums
class ResponseModality(str, Enum):
    """Output modality types."""

    IMAGE = "IMAGE"
    TEXT = "TEXT"


class ImageType(str, Enum):
    """Image source types."""

    S3 = "s3"
    LOCAL = "local"
    PIL = "pil"


# Type aliases for better clarity
ImagePath = Union[str, Path]  # File path or S3 URI
RawImageSource = Union[Image.Image, ImagePath]  # A raw image: PIL, file path, or S3 URI
LabeledImage = tuple[str, RawImageSource]  # Labeled image: ("label", image)
ImageSource = Union[RawImageSource, LabeledImage]  # Image or labeled image
OutputLocation = Union[str, Path]  # Where to save an image
LabeledOutput = tuple[str, OutputLocation]  # Labeled output: ("label", location)
OutputImageSpec = Union[OutputLocation, LabeledOutput]  # Output spec with optional label


class ImageInfo(BaseModel):
    """Metadata about an input image for logging purposes."""

    model_config = ConfigDict(frozen=True)

    label: str | None = Field(None, description="Optional label for the image")
    type: ImageType = Field(..., description="Type of image source")
    s3_uri: str | None = Field(None, description="S3 URI if type is 's3'")
    http_url: str | None = Field(None, description="HTTP URL if type is 's3'")
    local_path: str | None = Field(None, description="Local file path if type is 'local'")


class GenerationResult(BaseModel):
    """Result from image generation with support for multiple images and structured output."""

    model_config = ConfigDict(arbitrary_types_allowed=True, exclude_none=True)

    # Text or structured output (mutually exclusive)
    text: str | None = Field(None, description="Generated text response")
    structured: Any | None = Field(None, description="Structured output as Pydantic instance", exclude=True)

    # Multiple images support
    images: list[Image.Image] = Field(
        default_factory=list, description="List of generated PIL Images"
    )
    image_labels: list[str | None] = Field(
        default_factory=list, description="Labels for generated images"
    )
    image_locations: list[str] = Field(
        default_factory=list, description="Locations where images were saved"
    )
    image_s3_uris: list[str | None] = Field(
        default_factory=list, description="S3 URIs if saved to S3"
    )
    image_http_urls: list[str | None] = Field(
        default_factory=list, description="HTTP URLs if saved to S3"
    )

    # Backward compatibility - single image access (returns first image)
    @property
    def image(self) -> Image.Image | None:
        """Get first image for backward compatibility."""
        return self.images[0] if self.images else None

    @property
    def image_location(self) -> str | None:
        """Get first image location for backward compatibility."""
        return self.image_locations[0] if self.image_locations else None

    @property
    def image_s3_uri(self) -> str | None:
        """Get first S3 URI for backward compatibility."""
        return self.image_s3_uris[0] if self.image_s3_uris else None

    @property
    def image_http_url(self) -> str | None:
        """Get first HTTP URL for backward compatibility."""
        return self.image_http_urls[0] if self.image_http_urls else None


class GeminiImageGenerator:
    """
    Unified API for Gemini image generation with S3, structured output, and LangSmith support.

    This class provides a single generate() method that handles:
    - Text-to-image generation
    - Image editing with labeled inputs
    - Multi-image composition
    - Image analysis with structured output
    - Multiple image generation
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash-image",
        api_key: str | None = None,
        log_images: bool = True,
    ) -> None:
        """
        Initialize the Gemini image generator.

        Args:
            model_name: Name of the Gemini model to use for image generation
            api_key: Google API key (defaults to GOOGLE_API_KEY or GEMINI_API_KEY from env)
            log_images: Whether to log images to LangSmith traces (default: True)

        Note:
            The image model (gemini-2.5-flash-image) does not support structured output.
            For structured output, use a separate text model (gemini-2.5-flash) after
            image generation/analysis.
        """
        api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable, "
                "or pass api_key parameter."
            )

        genai.configure(api_key=api_key)
        self.model: genai.GenerativeModel = genai.GenerativeModel(model_name)
        self.model_name: str = model_name
        self.log_images: bool = log_images

    @traceable(
        name="generate",
        run_type="llm",
        metadata={"provider": "google", "capability": "unified_generation"},
    )
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        input_images: list[ImageSource] | None = None,
        temperature: float | None = None,
        # Output configuration
        output_images: list[OutputImageSpec] | None = None,
        output_text: bool = False,
        # LangSmith configuration
        run_name: str | None = None,
        metadata: dict[str, str] | None = None,  # noqa: ARG002 - used by @traceable decorator
        tags: list[str] | None = None,  # noqa: ARG002 - used by @traceable decorator
    ) -> GenerationResult:
        """
        Unified generation function with support for:
        - Labeled input images
        - Multiple output images
        - Flexible output combinations (image, text, or both)

        Args:
            prompt: User prompt text
            system_prompt: Optional system prompt for the model
            input_images: List of images, each can be:
                - PIL Image, str path, or Path
                - Tuple of ("label", image) for labeled images
            temperature: Sampling temperature (0.0 to 1.0)

            output_images: List of output image specifications, each can be:
                - str or Path (location to save)
                - Tuple of ("label", location) for labeled outputs
            output_text: If True, request text output

            metadata: Additional metadata to log in LangSmith
            tags: Tags to add to the LangSmith trace

        Returns:
            GenerationResult with:
                - text: str (if output_text=True)
                - images: List[Image] (if output_images specified)
                - image_labels, image_locations, image_s3_uris, image_http_urls

                Plus backward-compatible properties: image, image_location, image_s3_uri, image_http_url

        Note:
            The image model does not support structured output (JSON schemas).
            For structured output, use a separate call with gemini-2.5-flash:

            ```python
            # Step 1: Generate or analyze image
            result = generator.generate(
                prompt="Describe this image",
                input_images=["image.png"],
                output_text=True
            )

            # Step 2: Get structured output (separate model)
            from google import generativeai as genai
            text_model = genai.GenerativeModel("gemini-2.5-flash")

            response = text_model.generate_content(
                result.text + "\\n\\nFormat as JSON with fields: objects, colors, mood",
                generation_config={"response_mime_type": "application/json"}
            )
            ```

        Examples:
            # Labeled input images
            result = generator.generate(
                prompt="Blend the style from the product with the reference",
                input_images=[
                    ("Product photo:", "s3://bucket/product.png"),
                    ("Reference design:", "s3://bucket/reference.png")
                ],
                output_images=["s3://bucket/blended.png"]
            )

            # Multiple output images
            result = generator.generate(
                prompt="Create 3 variations of this scene",
                input_images=["input.png"],
                output_images=[
                    ("Variation 1", "s3://bucket/var1.png"),
                    ("Variation 2", "s3://bucket/var2.png"),
                    ("Variation 3", "s3://bucket/var3.png")
                ]
            )

            # Image + text
            result = generator.generate(
                prompt="Generate an image and explain it",
                output_images=["output.png"],
                output_text=True
            )

            # Image analysis (text only)
            result = generator.generate(
                prompt="Describe this image in detail",
                input_images=["image.png"],
                output_text=True
            )
        """
        # Set LangSmith run name if provided
        if run_name:
            try:
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.name = run_name
            except Exception:
                pass  # Silently ignore if LangSmith not available

        # Determine response modalities
        modalities = self._determine_response_modalities(
            output_images=output_images, output_text=output_text
        )

        # Load and prepare input images with labels
        content, image_infos = self._build_content_with_labels(prompt, system_prompt, input_images)

        # Log input images
        self._log_input_images(image_infos)

        # Call Gemini API
        response = self._call_gemini(
            content=content, temperature=temperature, modalities=modalities
        )

        # Extract and process results
        result = self._extract_response(response)

        # Parse output image specs
        output_specs = self._parse_output_specs(output_images) if output_images else []

        # Save and log output images if needed
        if result.images and output_specs:
            self._save_and_log_images(result, output_specs)

        # Log outputs to LangSmith
        self._log_outputs(result)

        return result

    def _determine_response_modalities(
        self, output_images: list[OutputImageSpec] | None, output_text: bool
    ) -> list[str]:
        """Determine what response modalities to request from Gemini."""
        modalities: list[str] = []

        if output_images:
            modalities.append(ResponseModality.IMAGE.value)

        if output_text:
            modalities.append(ResponseModality.TEXT.value)

        # Default to IMAGE if nothing specified
        return modalities if modalities else [ResponseModality.IMAGE.value]

    def _build_content_with_labels(
        self, prompt: str, system_prompt: str | None, input_images: list[ImageSource] | None
    ) -> tuple[list[Union[str, Image.Image, dict[str, Any]]], list[ImageInfo]]:
        """
        Build content list with labeled images interleaved.

        Returns:
            (content_list, image_infos)
        """
        content: list[Union[str, Image.Image, dict[str, Any]]] = []
        image_infos: list[ImageInfo] = []

        # Add system prompt if provided
        if system_prompt:
            content.append({"role": "system", "parts": [{"text": system_prompt}]})

        # Process input images with labels
        if input_images:
            for img_source in input_images:
                # Check if it's a labeled image tuple
                if isinstance(img_source, tuple) and len(img_source) == 2:
                    label, img = img_source
                    content.append(label)  # Add label text before image

                    # Load image and create metadata
                    loaded_img, info = self._load_single_image(img, label)
                    content.append(loaded_img)
                    image_infos.append(info)
                else:
                    # Regular unlabeled image
                    loaded_img, info = self._load_single_image(img_source, None)
                    content.append(loaded_img)
                    image_infos.append(info)

        # Add prompt at the end
        content.append(prompt)

        return content, image_infos

    def _load_single_image(
        self, img_source: RawImageSource, label: str | None
    ) -> tuple[Image.Image, ImageInfo]:
        """Load a single image and create its metadata."""
        if isinstance(img_source, (str, Path)):
            img_path = str(img_source)

            # Create metadata for logging
            if is_s3_uri(img_path):
                bucket, key = parse_s3_uri(img_path)
                http_url = get_http_url(bucket, key)
                info = ImageInfo(
                    label=label,
                    type=ImageType.S3,
                    s3_uri=img_path,
                    http_url=http_url,
                    local_path=None,
                )
            else:
                info = ImageInfo(
                    label=label,
                    type=ImageType.LOCAL,
                    local_path=img_path,
                    s3_uri=None,
                    http_url=None,
                )

            loaded_img = load_image(img_source)
        else:
            # PIL Image object
            loaded_img = img_source
            info = ImageInfo(
                label=label, type=ImageType.PIL, s3_uri=None, http_url=None, local_path=None
            )

        return loaded_img, info

    def _log_input_images(self, image_infos: list[ImageInfo]) -> None:
        """Log input images to LangSmith."""
        if not self.log_images or not image_infos:
            return

        try:
            run_tree: RunTree | None = get_current_run_tree()
            if not run_tree:
                return

            if not run_tree.inputs:
                run_tree.inputs = {}

            for idx, info in enumerate(image_infos):
                prefix = f"input_image_{idx}"
                if info.label:
                    run_tree.inputs[f"{prefix}_label"] = info.label
                if info.type == ImageType.S3:
                    run_tree.inputs[f"{prefix}_s3_uri"] = info.s3_uri
                    run_tree.inputs[f"{prefix}_http_url"] = info.http_url
                elif info.type == ImageType.LOCAL:
                    run_tree.inputs[f"{prefix}_local_path"] = info.local_path

        except Exception as e:
            print(f"Warning: Could not log input images to LangSmith: {e}")

    def _call_gemini(
        self,
        content: list[Union[str, Image.Image, dict[str, Any]]],
        temperature: float | None,
        modalities: list[str],
    ) -> GenerateContentResponse:
        """Call Gemini API and return response."""
        generation_config: dict[str, Any] = {
            "response_modalities": modalities,
        }

        # Add temperature if specified
        if temperature is not None:
            generation_config["temperature"] = temperature

        return self.model.generate_content(content, generation_config=generation_config)  # type: ignore[arg-type]

    def _extract_response(self, response: GenerateContentResponse) -> GenerationResult:
        """Extract text and images from Gemini response."""
        result = GenerationResult(text=None, structured=None)

        if not response.candidates:
            raise ValueError("No candidates in response")

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise ValueError("No content parts in response")

        # Extract text and images from parts
        for part in candidate.content.parts:
            # Handle text
            if hasattr(part, "text") and part.text:
                result.text = part.text

            # Handle images
            if self._has_image_data(part):
                img = self._extract_image_from_part(part)
                if img:
                    result.images.append(img)
                    result.image_labels.append(None)  # No label from response

        return result

    def _has_image_data(self, part: Any) -> bool:
        """Check if a response part contains image data."""
        return (
            hasattr(part, "inline_data")
            and part.inline_data is not None
            and hasattr(part.inline_data, "data")
            and part.inline_data.data
        )

    def _extract_image_from_part(self, part: Any) -> Image.Image | None:
        """Extract PIL Image from a response part."""
        try:
            if not hasattr(part, "inline_data") or not part.inline_data:
                return None

            image_data: bytes = part.inline_data.data
            return Image.open(BytesIO(image_data))
        except Exception as e:
            print(f"Warning: Could not process image data from response: {e}")
            return None

    def _parse_output_specs(
        self, output_images: list[OutputImageSpec]
    ) -> list[tuple[str | None, Union[str, Path]]]:
        """Parse output image specifications into (label, location) tuples."""
        specs: list[tuple[str | None, Union[str, Path]]] = []

        for spec in output_images:
            if isinstance(spec, tuple) and len(spec) == 2:
                label, location = spec
                specs.append((label, location))
            else:
                specs.append((None, spec))

        return specs

    def _save_and_log_images(
        self, result: GenerationResult, output_specs: list[tuple[str | None, Union[str, Path]]]
    ) -> None:
        """Save generated images and log to LangSmith."""
        # Match images with output specs
        for idx, (img, (label, location)) in enumerate(
            zip(result.images, output_specs, strict=False)
        ):
            # Save the image
            location_str, s3_uri, http_url = save_image(img, location)

            # Update result
            result.image_labels[idx] = label
            result.image_locations.append(location_str)
            result.image_s3_uris.append(s3_uri)
            result.image_http_urls.append(http_url)

            # Log to LangSmith
            if self.log_images:
                self._log_single_output_image(idx, label, s3_uri, http_url, location_str)

    def _log_single_output_image(
        self,
        idx: int,
        label: str | None,
        s3_uri: str | None,
        http_url: str | None,
        local_path: str | None,
    ) -> None:
        """Log a single output image to LangSmith."""
        try:
            run_tree: RunTree | None = get_current_run_tree()
            if not run_tree:
                return

            if not run_tree.outputs:
                run_tree.outputs = {}

            prefix = f"output_image_{idx}"
            if label:
                run_tree.outputs[f"{prefix}_label"] = label
            if s3_uri and http_url:
                run_tree.outputs[f"{prefix}_s3_uri"] = s3_uri
                run_tree.outputs[f"{prefix}_http_url"] = http_url
            elif local_path:
                run_tree.outputs[f"{prefix}_local_path"] = local_path

        except Exception as e:
            print(f"Warning: Could not log output image to LangSmith: {e}")

    def _log_outputs(self, result: GenerationResult) -> None:
        """Log text output to LangSmith."""
        if not self.log_images:
            return

        try:
            run_tree: RunTree | None = get_current_run_tree()
            if not run_tree:
                return

            if not run_tree.outputs:
                run_tree.outputs = {}

            if result.text:
                run_tree.outputs["text_response"] = result.text

        except Exception as e:
            print(f"Warning: Could not log outputs to LangSmith: {e}")
