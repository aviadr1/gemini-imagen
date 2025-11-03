"""
Gemini Image Generation with S3 and LangSmith Integration
==========================================================

This module provides a clean, unified API for Google Gemini image generation
with full S3 support and LangSmith tracing.

Main API:
    GeminiImageGenerator.generate() - Unified method supporting:
        - Labeled input images
        - Multiple output images
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

    # Structured output is not available from the image model. See the
    # "Structured Output Limitation" section in the README for details on the
    # current limitation.
"""

import asyncio
import os
import warnings
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

from .constants import (
    DEFAULT_GENERATION_MODEL,
    ENV_AWS_ACCESS_KEY_ID,
    ENV_AWS_SECRET_ACCESS_KEY,
    ENV_AWS_STORAGE_BUCKET_NAME,
    ENV_GEMINI_API_KEY,
    ENV_GOOGLE_API_KEY,
    ENV_GV_AWS_ACCESS_KEY_ID,
    ENV_GV_AWS_SECRET_ACCESS_KEY,
    ENV_GV_AWS_STORAGE_BUCKET_NAME,
)
from .models import GenerateParams
from .s3_utils import get_http_url, is_http_url, is_s3_uri, load_image, parse_s3_uri, save_image

if TYPE_CHECKING:
    from langsmith.run_trees import RunTree

# Suppress warnings about new finish reasons not yet in SDK enum
# This is expected as the API may add new finish reasons before SDK updates
warnings.filterwarnings(
    "ignore",
    message=".*is not a valid FinishReason.*",
    category=UserWarning,
    module="google.genai._common",
)

# Load environment variables
load_dotenv()


# Enums
class ResponseModality(str, Enum):
    """Output modality types."""

    IMAGE = "IMAGE"
    TEXT = "TEXT"


# Safety settings - re-export from google.genai.types for convenience
SafetySetting = types.SafetySetting
HarmCategory = types.HarmCategory
HarmBlockThreshold = types.HarmBlockThreshold


# Constants for image generation
PRESET_ASPECT_RATIOS = {
    "1:1",  # Square (default, 1024x1024)
    "3:4",  # Portrait fullscreen
    "4:3",  # Fullscreen/landscape
    "9:16",  # Portrait/tall (social media)
    "16:9",  # Widescreen
}


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
    """Result from image generation with support for multiple images."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Text output from the model (structured output is unavailable for image models)
    text: str | None = Field(None, description="Generated text response")
    structured: Any | None = Field(
        None,
        description=(
            "Reserved for compatibility with text models. The Gemini image model does "
            "not provide structured output."
        ),
        exclude=True,
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
    Unified API for Gemini image generation with S3 and LangSmith support.

    This class provides a single generate() method that handles:
    - Text-to-image generation
    - Image editing with labeled inputs
    - Multi-image composition
    - Multiple image generation
    """

    def __init__(
        self,
        model_name: str = DEFAULT_GENERATION_MODEL,
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
            Requests for JSON schemas will be ignored by the API.
        """
        api_key = api_key or os.getenv(ENV_GOOGLE_API_KEY) or os.getenv(ENV_GEMINI_API_KEY)

        if not api_key:
            raise ValueError(
                f"No API key found. Set {ENV_GOOGLE_API_KEY} or {ENV_GEMINI_API_KEY} environment variable, "
                "or pass api_key parameter."
            )

        self.client = genai.Client(api_key=api_key)
        self.model_name: str = model_name
        self.log_images: bool = log_images

        # Store AWS credentials for S3 operations
        self.aws_access_key_id = (
            aws_access_key_id
            or os.getenv(ENV_GV_AWS_ACCESS_KEY_ID)
            or os.getenv(ENV_AWS_ACCESS_KEY_ID)
        )
        self.aws_secret_access_key = (
            aws_secret_access_key
            or os.getenv(ENV_GV_AWS_SECRET_ACCESS_KEY)
            or os.getenv(ENV_AWS_SECRET_ACCESS_KEY)
        )
        self.aws_storage_bucket_name = (
            aws_storage_bucket_name
            or os.getenv(ENV_GV_AWS_STORAGE_BUCKET_NAME)
            or os.getenv(ENV_AWS_STORAGE_BUCKET_NAME)
        )
        self.aws_region = aws_region

    @staticmethod
    def list_models(api_key: str | None = None) -> list[dict[str, Any]]:
        """
        List all available models from Google AI API.

        Args:
            api_key: Google API key. If None, uses GOOGLE_API_KEY or GEMINI_API_KEY env var.

        Returns:
            List of model dictionaries with keys: name, display_name, methods, description

        Example:
            >>> models = GeminiImageGenerator.list_models()
            >>> for model in models:
            ...     print(f"{model['name']}: {model['methods']}")
        """
        import os

        if api_key is None:
            api_key = os.getenv(ENV_GOOGLE_API_KEY) or os.getenv(ENV_GEMINI_API_KEY)
            if not api_key:
                raise ValueError(
                    f"API key required. Set {ENV_GOOGLE_API_KEY} environment variable or pass api_key parameter."
                )

        client = genai.Client(api_key=api_key)

        models = []
        for model in client.models.list():
            # Get supported methods (attribute name may vary)
            methods = getattr(model, "supported_generation_methods", None)
            if methods is None:
                methods = getattr(model, "supported_actions", [])

            models.append(
                {
                    "name": model.name,
                    "display_name": model.display_name,
                    "methods": methods,
                    "description": model.description,
                }
            )

        return models

    @traceable(
        name="generate",
        run_type="llm",
        metadata={"provider": "google", "capability": "unified_generation"},
    )
    async def generate(
        self,
        prompt: str | GenerateParams | None = None,
        system_prompt: str | None = None,
        input_images: list[ImageSource] | None = None,
        temperature: float | None = None,
        # Image generation configuration
        aspect_ratio: str | tuple[int, int] | None = None,
        # Safety configuration
        safety_settings: list[types.SafetySetting] | None = None,
        # Output configuration
        output_images: list[OutputImageSpec] | OutputImageSpec | None = None,
        output_text: bool = False,
        # LangSmith configuration
        run_name: str | None = None,
        metadata: dict[str, str] | None = None,  # - used by @traceable decorator
        tags: list[str] | None = None,  # - used by @traceable decorator
    ) -> GenerationResult:
        """
        Unified generation function with support for:
        - Labeled input images
        - Multiple output images (duplicates - same image saved to multiple locations)
        - Flexible output combinations (image, text, or both)
        - Custom aspect ratios

        Supported Features (gemini-2.5-flash-image):
        ============================================
            ✓ aspect_ratio - Control image dimensions (1:1, 16:9, etc.)
            ✓ Multiple output_images - Saves same image to multiple locations
            ✓ Labeled inputs - Reference input images by name in prompts
            ✓ Image + text output - Generate both image and text description
            ✓ S3 integration - Load from and save to S3

        Limitations:
        ============
            ✗ Resolution control - Resolution is auto-determined based on aspect ratio
            ✗ Multiple variations - Only 1 image generated per call (can save to multiple locations)

        Args:
            prompt: User prompt text
            system_prompt: Optional system prompt for the model
            input_images: List of images, each can be:
                - PIL Image, str path, or Path
                - Tuple of ("label", image) for labeled images
            temperature: Sampling temperature (0.0 to 1.0)

            aspect_ratio: Image aspect ratio
                - Preset string: "1:1" (default), "3:4", "4:3", "9:16", "16:9"
                - Custom tuple: (16, 10) for any custom aspect ratio
                - None: Uses default (1:1 square, 1024x1024)

            safety_settings: Optional list of SafetySetting objects to control content filtering
                - None: Use Gemini's default safety settings (BLOCK_MEDIUM_AND_ABOVE)
                - List of SafetySetting(category=HarmCategory.X, threshold=HarmBlockThreshold.Y)
                - Available categories: HARM_CATEGORY_SEXUALLY_EXPLICIT, HARM_CATEGORY_HARASSMENT,
                  HARM_CATEGORY_HATE_SPEECH, HARM_CATEGORY_DANGEROUS_CONTENT, etc.
                - Available thresholds:
                  * BLOCK_NONE: Disable blocking for this category
                  * BLOCK_ONLY_HIGH: Relaxed, block only high-probability harmful content
                  * BLOCK_MEDIUM_AND_ABOVE: Default, block medium and high
                  * BLOCK_LOW_AND_ABOVE: Strict, block low, medium, and high
                - Example: [SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                           threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH)]

            output_images: Where to save generated image(s)
                - Single: str/Path or ("label", str/Path)
                - Multiple: List of above formats (same image saved to all locations)
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
            The image model does not support structured output (JSON schemas), so
            requests for structured data will return plain text instead.

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
        # Handle both Pydantic model and individual parameters
        if isinstance(prompt, GenerateParams):
            # Using Pydantic model - extract all parameters
            params_dict = prompt.model_dump(exclude_none=True)
            prompt = params_dict.pop("prompt")
            system_prompt = params_dict.get("system_prompt", system_prompt)
            input_images = params_dict.get("input_images", input_images)
            temperature = params_dict.get("temperature", temperature)
            aspect_ratio = params_dict.get("aspect_ratio", aspect_ratio)
            safety_settings = params_dict.get("safety_settings", safety_settings)
            output_images = params_dict.get("output_images", output_images)
            output_text = params_dict.get("output_text", output_text)
            run_name = params_dict.get("run_name", run_name)
            metadata = params_dict.get("metadata", metadata)
            tags = params_dict.get("tags", tags)

        # Type check: ensure prompt is a string at this point
        assert isinstance(prompt, str), "prompt must be a string"

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
            safety_settings=safety_settings,
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
        safety_settings: list[types.SafetySetting] | None = None,
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

        # Add safety settings if specified
        if safety_settings is not None:
            config_params["safety_settings"] = safety_settings

        # Add image generation parameters
        # Build ImageConfig with available parameters
        image_config_params: dict[str, Any] = {}

        # aspect_ratio is supported on all models
        if aspect_ratio is not None:
            image_config_params["aspect_ratio"] = aspect_ratio

        # Create ImageConfig if we have any parameters
        if image_config_params:
            config_params["image_config"] = types.ImageConfig(**image_config_params)

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

    def _interpret_finish_reason(self, finish_reason: types.FinishReason) -> str:
        """Provide human-readable interpretation of finish reason."""
        interpretations = {
            types.FinishReason.STOP: "Generation completed successfully",
            types.FinishReason.NO_IMAGE: "No image generated - likely blocked by safety filters or content policy",
            types.FinishReason.IMAGE_SAFETY: "Image generation blocked due to safety policy violation",
            types.FinishReason.SAFETY: "Content blocked due to safety policy violation",
            types.FinishReason.PROHIBITED_CONTENT: "Content blocked - prohibited by content policy",
            types.FinishReason.IMAGE_PROHIBITED_CONTENT: "Image content blocked - prohibited by content policy",
            types.FinishReason.BLOCKLIST: "Content blocked - matched blocklist",
            types.FinishReason.SPII: "Content blocked - contains sensitive personal information",
            types.FinishReason.MAX_TOKENS: "Generation stopped - reached maximum token limit",
            types.FinishReason.RECITATION: "Content blocked - potential copyright/recitation issue",
            types.FinishReason.LANGUAGE: "Content blocked - language not supported",
            types.FinishReason.MALFORMED_FUNCTION_CALL: "Generation failed - malformed function call",
            types.FinishReason.OTHER: "Generation stopped for unspecified reason",
        }

        # Handle finish reason by string name if not found in enum
        # This handles new finish reasons like IMAGE_OTHER that may not be in the SDK yet
        finish_reason_str = str(finish_reason)
        if "IMAGE_OTHER" in finish_reason_str:
            return "Image generation completed with alternative format or method"

        return interpretations.get(finish_reason, f"Unknown finish reason: {finish_reason}")

    def _format_safety_info(
        self, response: types.GenerateContentResponse, candidate: types.Candidate | None = None
    ) -> dict[str, Any]:
        """
        Extract safety information from response for logging.

        Stores actual SDK objects directly. LangSmith will serialize them automatically.
        """
        safety_info: dict[str, Any] = {}

        # Store entire prompt_feedback object if present
        if response.prompt_feedback is not None:
            safety_info["prompt_feedback"] = response.prompt_feedback

        # Store entire candidate object if present
        if candidate is not None:
            safety_info["candidate"] = candidate

        return safety_info

    def _log_response_to_langsmith(
        self, response: types.GenerateContentResponse, safety_info: dict[str, Any]
    ) -> None:
        """Log complete response and safety information to LangSmith."""
        if not self.log_images:
            return

        try:
            from langsmith import get_current_run_tree

            run_tree = get_current_run_tree()
            if run_tree and run_tree.outputs is not None:
                # Log entire response object - LangSmith will serialize it
                run_tree.outputs["gemini_response"] = response

                # Log finish reason interpretation if present
                if "candidate" in safety_info:
                    candidate_info = safety_info["candidate"]
                    if candidate_info.finish_reason:
                        run_tree.outputs["finish_reason_interpretation"] = (
                            self._interpret_finish_reason(candidate_info.finish_reason)
                        )

        except Exception as e:
            print(f"Warning: Could not log response info to LangSmith: {e}")

    def _extract_response(self, response: types.GenerateContentResponse) -> GenerationResult:
        """Extract text and images from Gemini response."""
        result = GenerationResult(text=None, structured=None)

        if not response.candidates:
            # Check if prompt was blocked
            safety_info = self._format_safety_info(response)
            self._log_response_to_langsmith(response, safety_info)

            # Serialize response for debugging
            import json

            response_dict = response.model_dump(exclude_none=True)
            response_json = json.dumps(response_dict, indent=2, default=str)

            # Create detailed error message with clear summary
            error_msg = "❌ CONTENT GENERATION FAILED: No candidates in response"
            if "prompt_feedback" in safety_info:
                prompt_feedback = safety_info["prompt_feedback"]
                if prompt_feedback.block_reason:
                    error_msg += "\n\nReason: Prompt blocked by content policy"
                    error_msg += f"\nBlock reason: {prompt_feedback.block_reason}"
                    if prompt_feedback.block_reason_message:
                        error_msg += f"\nMessage: {prompt_feedback.block_reason_message}"
                if prompt_feedback.safety_ratings:
                    error_msg += f"\nSafety ratings: {prompt_feedback.safety_ratings}"

            error_msg += f"\n\nModel: {response.model_version}"
            error_msg += f"\nResponse ID: {response.response_id}"
            error_msg += f"\n\nFull response:\n{response_json}"
            raise ValueError(error_msg)

        candidate = response.candidates[0]

        # Check if content was blocked or empty
        if not candidate.content or not candidate.content.parts:
            # Extract and log safety information
            safety_info = self._format_safety_info(response, candidate)
            self._log_response_to_langsmith(response, safety_info)

            # Serialize response for debugging
            import json

            response_dict = response.model_dump(exclude_none=True)
            response_json = json.dumps(response_dict, indent=2, default=str)

            # Create detailed error message with clear summary
            error_msg = "❌ CONTENT GENERATION FAILED: No content generated"
            if "candidate" in safety_info:
                candidate_info = safety_info["candidate"]
                if candidate_info.finish_reason:
                    interpretation = self._interpret_finish_reason(candidate_info.finish_reason)
                    error_msg += f"\n\n{interpretation}"
                    error_msg += f"\nFinish reason: {candidate_info.finish_reason}"
                if candidate_info.finish_message:
                    error_msg += f"\nFinish message: {candidate_info.finish_message}"
                if candidate_info.safety_ratings:
                    error_msg += f"\nSafety ratings: {candidate_info.safety_ratings}"

            error_msg += f"\n\nModel: {response.model_version}"
            error_msg += f"\nResponse ID: {response.response_id}"
            if response.usage_metadata:
                error_msg += f"\nTokens used: {response.usage_metadata.total_token_count}"
            error_msg += f"\n\nFull response:\n{response_json}"
            raise ValueError(error_msg)

        # Extract text and images from parts
        for part in candidate.content.parts:
            # Handle text
            if part.text:
                result.text = part.text

            # Handle images
            if self._has_image_data(part):
                img = self._extract_image_from_part(part)
                if img:
                    result.images.append(img)
                    result.image_labels.append(None)  # No label from response

        # Log successful response metadata to LangSmith
        safety_info = self._format_safety_info(response, candidate)
        self._log_response_to_langsmith(response, safety_info)

        return result

    def _has_image_data(self, part: Any) -> bool:
        """Check if a response part contains image data."""
        return (
            part.inline_data is not None
            and part.inline_data.data is not None
            and len(part.inline_data.data) > 0
        )

    def _extract_image_from_part(self, part: Any) -> Image.Image | None:
        """Extract PIL Image from a response part."""
        try:
            if part.inline_data is None or part.inline_data.data is None:
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
