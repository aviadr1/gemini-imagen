"""
Constants for gemini-imagen.

This module defines constants used throughout the library to avoid magic strings
and ensure consistency.
"""

# Model constants
# Gemini models for different use cases

# Image generation model - supports image output modalities
DEFAULT_GENERATION_MODEL = "gemini-2.5-flash-image"

# Image analysis model - fast text-based understanding
DEFAULT_ANALYSIS_MODEL = "gemini-2.5-flash"

# Deprecated - kept for backward compatibility
DEPRECATED_DEFAULT_MODEL = DEFAULT_GENERATION_MODEL
