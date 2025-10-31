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

import asyncio
import os
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from dotenv import load_dotenv
from google import genai
from google.genai import types
from langsmith import get_current_run_tree, traceable
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from .s3_utils import get_http_url, is_http_url, is_s3_uri, load_image, parse_s3_uri, save_image

if TYPE_CHECKING:
    from langsmith.run_trees import RunTree

# Load environment variables
load_dotenv()


# Enums
class ResponseModality(str, Enum):
    """Output modality types."""

    IMAGE = "IMAGE"
    TEXT = "TEXT"


# Constants for image generation
PRESET_ASPECT_RATIOS = {
    "1:1",  # Square (default, 1024x1024)
    "3:4",  # Portrait fullscreen
    "4:3",  # Fullscreen/landscape
    "9:16",  # Portrait/tall (social media)
    "16:9",  # Widescreen
}

VALID_IMAGE_SIZES = {"1K", "2K"}  # 2K only supported on Standard/Ultra models


def _normalize_aspect_ratio(aspect_ratio: str | tuple[int, int] | None) -> str | None:
    """
    Normalize aspect ratio to string format.

    Args:
        aspect_ratio: Either a preset string ("16:9"), custom tuple (16, 9), or None

    Returns:
        Normalized aspect ratio string or None

    Raises:
        ValueError: If aspect ratio format is invalid
    """
    if aspect_ratio is None:
        return None

    if isinstance(aspect_ratio, str):
        # Validate format
        if ":" not in aspect_ratio:
            raise ValueError(
                f"Invalid aspect ratio string: {aspect_ratio}. Must be in format 'W:H' (e.g., '16:9')"
            )
        return aspect_ratio

    if isinstance(aspect_ratio, tuple):
        if len(aspect_ratio) != 2:
            raise ValueError(f"Invalid aspect ratio tuple: {aspect_ratio}. Must be (width, height)")
        width, height = aspect_ratio
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError(
                f"Invalid aspect ratio values: {aspect_ratio}. Both width and height must be integers"
            )
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Invalid aspect ratio values: {aspect_ratio}. Both width and height must be positive"
            )
        return f"{width}:{height}"

    raise ValueError(f"Invalid aspect ratio type: {type(aspect_ratio)}. Must be string or tuple")


class ImageType(str, Enum):
    """Image source types."""

    S3 = "s3"
    LOCAL = "local"
    PIL = "pil"
    HTTP = "http"


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
    http_url: str | None = Field(None, description="HTTP URL if type is 's3' or 'http'")
    local_path: str | None = Field(None, description="Local file path if type is 'local'")


class GenerationResult(BaseModel):
    """Result from image generation with support for multiple images and structured output."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Text or structured output (mutually exclusive)
    text: str | None = Field(None, description="Generated text response")
    structured: Any | None = Field(
        None, description="Structured output as Pydantic instance", exclude=True
    )

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
        # AWS S3 credentials (optional, defaults to environment variables)
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_storage_bucket_name: str | None = None,
        aws_region: str = "us-east-1",
    ) -> None:
        """
        Initialize the Gemini image generator.

        Args:
            model_name: Name of the Gemini model to use for image generation
            api_key: Google API key (defaults to GOOGLE_API_KEY or GEMINI_API_KEY from env)
            log_images: Whether to log images to LangSmith traces (default: True)
            aws_access_key_id: AWS access key ID (defaults to GV_AWS_ACCESS_KEY_ID or AWS_ACCESS_KEY_ID from env)
            aws_secret_access_key: AWS secret access key (defaults to GV_AWS_SECRET_ACCESS_KEY or AWS_SECRET_ACCESS_KEY from env)
            aws_storage_bucket_name: Default S3 bucket name (defaults to GV_AWS_STORAGE_BUCKET_NAME or AWS_STORAGE_BUCKET_NAME from env)
            aws_region: AWS region for S3 operations (default: us-east-1)

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

        self.client = genai.Client(api_key=api_key)
        self.model_name: str = model_name
        self.log_images: bool = log_images

        # Store AWS credentials for S3 operations
        self.aws_access_key_id = (
            aws_access_key_id or os.getenv("GV_AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
        )
        self.aws_secret_access_key = (
            aws_secret_access_key
            or os.getenv("GV_AWS_SECRET_ACCESS_KEY")
            or os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        self.aws_storage_bucket_name = (
            aws_storage_bucket_name
            or os.getenv("GV_AWS_STORAGE_BUCKET_NAME")
            or os.getenv("AWS_STORAGE_BUCKET_NAME")
        )
        self.aws_region = aws_region

    @traceable(
        name="generate",
        run_type="llm",
        metadata={"provider": "google", "capability": "unified_generation"},
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        input_images: list[ImageSource] | None = None,
        temperature: float | None = None,
        # Image generation configuration
        aspect_ratio: str | tuple[int, int] | None = None,
        image_size: str | None = None,
        # Output configuration
        output_images: list[OutputImageSpec] | OutputImageSpec | None = None,
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
        - Custom aspect ratios and resolutions

        Args:
            prompt: User prompt text
            system_prompt: Optional system prompt for the model
            input_images: List of images, each can be:
                - PIL Image, str path, or Path
                - Tuple of ("label", image) for labeled images
            temperature: Sampling temperature (0.0 to 1.0)

            aspect_ratio: Image aspect ratio. Options:
                - Preset string: "1:1", "3:4", "4:3", "9:16", "16:9"
                - Custom tuple: (16, 10) for 16:10 ratio
                - None: Uses default (1:1)
            image_size: Image resolution (NOT SUPPORTED on gemini-2.5-flash-image)
                - Only available on Imagen models (imagen-3, imagen-4)
                - Options: "1K" (default), "2K" (higher resolution)
                - This parameter will be ignored with a warning for Gemini models
                - None: Uses model default

            output_images: List of output image specifications, each can be:
                - str or Path (location to save)
                - Tuple of ("label", location) for labeled outputs
                - NOTE: gemini-2.5-flash-image only generates 1 image per API call
                - Multiple outputs will use the same generated image saved to different locations
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
            from google import genai
            from google.genai import types

            client = genai.Client(api_key='your-api-key')
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=result.text + "\\n\\nFormat as JSON with fields: objects, colors, mood",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
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

        # Validate and normalize aspect ratio
        normalized_aspect_ratio = _normalize_aspect_ratio(aspect_ratio)

        # Validate image size
        if image_size is not None and image_size not in VALID_IMAGE_SIZES:
            raise ValueError(
                f"Invalid image_size: {image_size}. Must be one of {VALID_IMAGE_SIZES}"
            )

        # Determine number of images to generate based on output_images
        if output_images is not None:
            output_specs = self._parse_output_specs(output_images)
            number_of_images = len(output_specs) if output_specs else 1
        else:
            number_of_images = 1

        # Determine response modalities
        modalities = self._determine_response_modalities(
            output_images=output_images, output_text=output_text
        )

        # Load and prepare input images with labels
        content, image_infos = await self._build_content_with_labels(prompt, input_images)

        # Log input images
        self._log_input_images(image_infos)

        # Call Gemini API
        response = await self._call_gemini(
            content=content,
            system_prompt=system_prompt,
            temperature=temperature,
            modalities=modalities,
            aspect_ratio=normalized_aspect_ratio,
            image_size=image_size,
            number_of_images=number_of_images,
        )

        # Extract and process results
        result = self._extract_response(response)

        # Parse output image specs
        output_specs = self._parse_output_specs(output_images) if output_images else []

        # Save and log output images if needed
        if result.images and output_specs:
            await self._save_and_log_images(result, output_specs)

        # Log outputs to LangSmith
        self._log_outputs(result)

        return result

    def _determine_response_modalities(
        self, output_images: list[OutputImageSpec] | OutputImageSpec | None, output_text: bool
    ) -> list[str]:
        """Determine what response modalities to request from Gemini."""
        modalities: list[str] = []

        if output_images:
            modalities.append(ResponseModality.IMAGE.value)

        if output_text:
            modalities.append(ResponseModality.TEXT.value)

        # Default to IMAGE if nothing specified
        return modalities if modalities else [ResponseModality.IMAGE.value]

    async def _build_content_with_labels(
        self, prompt: str, input_images: list[ImageSource] | None
    ) -> tuple[list[Union[str, Image.Image, dict[str, Any]]], list[ImageInfo]]:
        """
        Build content list with labeled images interleaved.

        Returns:
            (content_list, image_infos)

        Note: system_prompt is handled separately in _call_gemini() via the
        config's system_instruction parameter, not in the content list.
        """
        content: list[Union[str, Image.Image, dict[str, Any]]] = []
        image_infos: list[ImageInfo] = []

        # Process input images with labels
        if input_images:
            # Prepare all image loading tasks
            load_tasks: list[tuple[str | None, RawImageSource]] = []
            for img_source in input_images:
                # Check if it's a labeled image tuple
                if isinstance(img_source, tuple) and len(img_source) == 2:
                    label_str, img = img_source
                    load_tasks.append((label_str, img))
                else:
                    # Regular unlabeled image
                    load_tasks.append((None, img_source))

            # Load all images in parallel using asyncio.gather
            loaded_results = await asyncio.gather(
                *[self._load_single_image(img, label) for label, img in load_tasks]
            )

            # Build content list with labels interleaved in correct order
            for (label, _), (loaded_img, info) in zip(load_tasks, loaded_results, strict=False):
                if label:
                    content.append(label)  # Add label text before image
                content.append(loaded_img)
                image_infos.append(info)

        # Add prompt at the end
        content.append(prompt)

        return content, image_infos

    async def _load_single_image(
        self, img_source: RawImageSource, label: str | None
    ) -> tuple[Image.Image, ImageInfo]:
        """Load a single image and create its metadata."""
        if isinstance(img_source, str | Path):
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
            elif is_http_url(img_path):
                info = ImageInfo(
                    label=label,
                    type=ImageType.HTTP,
                    http_url=img_path,
                    s3_uri=None,
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

            loaded_img = await load_image(
                img_source,
                access_key_id=self.aws_access_key_id,
                secret_access_key=self.aws_secret_access_key,
            )
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
                elif info.type == ImageType.HTTP:
                    run_tree.inputs[f"{prefix}_http_url"] = info.http_url
                elif info.type == ImageType.LOCAL:
                    run_tree.inputs[f"{prefix}_local_path"] = info.local_path

        except Exception as e:
            print(f"Warning: Could not log input images to LangSmith: {e}")

    async def _call_gemini(
        self,
        content: list[Union[str, Image.Image, dict[str, Any]]],
        system_prompt: str | None,
        temperature: float | None,
        modalities: list[str],
        aspect_ratio: str | None = None,
        image_size: str | None = None,
        number_of_images: int = 1,
    ) -> types.GenerateContentResponse:
        """Call Gemini API and return response."""
        import asyncio

        config_params: dict[str, Any] = {
            "response_modalities": modalities,
        }

        # Add temperature if specified
        if temperature is not None:
            config_params["temperature"] = temperature

        # Add system instruction if specified
        if system_prompt is not None:
            config_params["system_instruction"] = system_prompt

        # Add image generation parameters
        # aspect_ratio goes in ImageConfig
        if aspect_ratio is not None:
            config_params["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

        # Note: number_of_images and image_size are NOT supported on gemini-2.5-flash-image
        # They are only available on Imagen models (imagen-3, imagen-4)
        # For Gemini models, you can only generate 1 image at a time per API call
        if number_of_images > 1:
            import warnings

            warnings.warn(
                f"number_of_images parameter ({number_of_images}) is not supported on {self.model_name}. "
                "It's only available on Imagen models. "
                "The model will generate 1 image per API call. "
                "To generate multiple images, make multiple API calls.",
                UserWarning,
                stacklevel=2,
            )

        if image_size is not None:
            import warnings

            warnings.warn(
                f"image_size parameter ({image_size}) is not supported on {self.model_name}. "
                "It's only available on Imagen models (imagen-3, imagen-4). "
                "This parameter will be ignored.",
                UserWarning,
                stacklevel=2,
            )

        config = types.GenerateContentConfig(**config_params)

        # Run the Gemini API call in executor since it's synchronous
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model_name,
                contents=content,  # type: ignore[arg-type]
                config=config,
            ),
        )

    def _extract_response(self, response: types.GenerateContentResponse) -> GenerationResult:
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
        self, output_images: list[OutputImageSpec] | OutputImageSpec
    ) -> list[tuple[str | None, Union[str, Path]]]:
        """Parse output image specifications into (label, location) tuples."""
        # Normalize to list if single spec provided
        specs_list: list[OutputImageSpec] = (
            [output_images] if not isinstance(output_images, list) else output_images
        )

        specs: list[tuple[str | None, Union[str, Path]]] = []

        for spec in specs_list:
            if isinstance(spec, tuple) and len(spec) == 2:
                label, location = spec
                specs.append((label, location))
            else:
                specs.append((None, spec))

        return specs

    async def _save_and_log_images(
        self, result: GenerationResult, output_specs: list[tuple[str | None, Union[str, Path]]]
    ) -> None:
        """Save generated images and log to LangSmith."""
        # Prepare save tasks for parallel execution
        save_tasks = [
            save_image(
                img,
                location,
                region=self.aws_region,
                access_key_id=self.aws_access_key_id,
                secret_access_key=self.aws_secret_access_key,
            )
            for img, (label, location) in zip(result.images, output_specs, strict=False)
        ]

        # Save all images in parallel using asyncio.gather
        save_results = await asyncio.gather(*save_tasks)

        # Update result and log to LangSmith
        for idx, ((label, _), (location_str, s3_uri, http_url)) in enumerate(
            zip(output_specs, save_results, strict=False)
        ):
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
