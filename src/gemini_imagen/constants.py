"""
Constants for gemini-imagen.

This module defines constants used throughout the library to avoid magic strings
and ensure consistency.
"""

from google.genai import types

# Model constants
# Gemini models for different use cases

# Image generation model - supports image output modalities
DEFAULT_GENERATION_MODEL = "gemini-2.5-flash-image"

# Image analysis model - fast text-based understanding
DEFAULT_ANALYSIS_MODEL = "gemini-2.5-flash"

# Deprecated - kept for backward compatibility
DEPRECATED_DEFAULT_MODEL = DEFAULT_GENERATION_MODEL

# Environment variable names
ENV_GOOGLE_API_KEY = "GOOGLE_API_KEY"
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
ENV_AWS_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
ENV_AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
ENV_AWS_STORAGE_BUCKET_NAME = "AWS_STORAGE_BUCKET_NAME"
ENV_GV_AWS_ACCESS_KEY_ID = "GV_AWS_ACCESS_KEY_ID"
ENV_GV_AWS_SECRET_ACCESS_KEY = "GV_AWS_SECRET_ACCESS_KEY"
ENV_GV_AWS_STORAGE_BUCKET_NAME = "GV_AWS_STORAGE_BUCKET_NAME"
ENV_LANGSMITH_API_KEY = "LANGSMITH_API_KEY"
ENV_LANGSMITH_PROJECT = "LANGSMITH_PROJECT"
ENV_LANGSMITH_TRACING = "LANGSMITH_TRACING"

# Config file keys
CONFIG_KEY_GOOGLE_API_KEY = "google_api_key"
CONFIG_KEY_AWS_ACCESS_KEY_ID = "aws_access_key_id"
CONFIG_KEY_AWS_SECRET_ACCESS_KEY = "aws_secret_access_key"
CONFIG_KEY_AWS_STORAGE_BUCKET_NAME = "aws_storage_bucket_name"
CONFIG_KEY_LANGSMITH_API_KEY = "langsmith_api_key"
CONFIG_KEY_LANGSMITH_PROJECT = "langsmith_project"
CONFIG_KEY_LANGSMITH_TRACING = "langsmith_tracing"
CONFIG_KEY_DEFAULT_MODEL = "default_model"
CONFIG_KEY_TEMPERATURE = "temperature"
CONFIG_KEY_ASPECT_RATIO = "aspect_ratio"
CONFIG_KEY_SAFETY_SETTINGS = "safety_settings"

# Safety setting shortcuts for CLI
# Maps user-friendly names to HarmBlockThreshold enum values
SAFETY_PRESETS = {
    "strict": types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    "default": types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "relaxed": types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "none": types.HarmBlockThreshold.BLOCK_NONE,
}

# Re-export enums for convenience
HarmCategory = types.HarmCategory
HarmBlockThreshold = types.HarmBlockThreshold
SafetySetting = types.SafetySetting
