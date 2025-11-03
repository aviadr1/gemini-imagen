"""
Configuration management for gemini-imagen CLI.

Handles loading and saving configuration from multiple sources:
1. CLI flags (highest priority)
2. Environment variables
3. Config file (~/.config/imagen/config.yaml)
4. Defaults (lowest priority)
"""

import os
from pathlib import Path
from typing import Any

import yaml

from ..constants import (
    CONFIG_KEY_ASPECT_RATIO,
    CONFIG_KEY_AWS_ACCESS_KEY_ID,
    CONFIG_KEY_AWS_SECRET_ACCESS_KEY,
    CONFIG_KEY_AWS_STORAGE_BUCKET_NAME,
    CONFIG_KEY_DEFAULT_MODEL,
    CONFIG_KEY_GOOGLE_API_KEY,
    CONFIG_KEY_LANGSMITH_API_KEY,
    CONFIG_KEY_LANGSMITH_PROJECT,
    CONFIG_KEY_LANGSMITH_TRACING,
    CONFIG_KEY_SAFETY_SETTINGS,
    CONFIG_KEY_TEMPERATURE,
    DEFAULT_ANALYSIS_MODEL,
    DEFAULT_GENERATION_MODEL,
    ENV_GEMINI_API_KEY,
    ENV_GOOGLE_API_KEY,
    ENV_GV_AWS_ACCESS_KEY_ID,
    ENV_GV_AWS_SECRET_ACCESS_KEY,
    ENV_GV_AWS_STORAGE_BUCKET_NAME,
    ENV_LANGSMITH_API_KEY,
    ENV_LANGSMITH_PROJECT,
    ENV_LANGSMITH_TRACING,
)


class Config:
    """Configuration manager for gemini-imagen CLI."""

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Custom config directory (default: ~/.config/imagen)
        """
        if config_dir is None:
            # Follow XDG Base Directory Specification
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config_home:
                config_dir = Path(xdg_config_home) / "imagen"
            else:
                config_dir = Path.home() / ".config" / "imagen"

        self.config_dir = config_dir
        self.config_file = config_dir / "config.yaml"
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            with self.config_file.open() as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}

    def _save(self) -> None:
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with self.config_file.open("w") as f:
            yaml.safe_dump(self._config, f, default_flow_style=False, sort_keys=False)

    def get(self, key: str, default: Any = None, env_var: str | None = None) -> Any:
        """
        Get configuration value with precedence:
        1. Environment variable (if env_var provided)
        2. Config file
        3. Default value

        Args:
            key: Configuration key
            default: Default value if not found
            env_var: Environment variable name to check

        Returns:
            Configuration value
        """
        # Check environment variable first
        if env_var and env_var in os.environ:
            return os.environ[env_var]

        # Check config file
        if key in self._config:
            return self._config[key]

        # Return default
        return default

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value and save to file.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
        self._save()

    def delete(self, key: str) -> bool:
        """
        Delete configuration key.

        Args:
            key: Configuration key to delete

        Returns:
            True if key existed and was deleted, False otherwise
        """
        if key in self._config:
            del self._config[key]
            self._save()
            return True
        return False

    def list_all(self) -> dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dictionary of all configuration values
        """
        return self._config.copy()

    def get_path(self) -> Path:
        """
        Get path to configuration file.

        Returns:
            Path to config file
        """
        return self.config_file

    # Convenience methods for common config keys
    def get_google_api_key(self) -> str | None:
        """Get Google API key from config or environment."""
        return self.get(
            CONFIG_KEY_GOOGLE_API_KEY,
            env_var=ENV_GOOGLE_API_KEY,
        ) or self.get(CONFIG_KEY_GOOGLE_API_KEY, env_var=ENV_GEMINI_API_KEY)

    def get_aws_access_key_id(self) -> str | None:
        """Get AWS access key ID from config or environment."""
        return self.get(CONFIG_KEY_AWS_ACCESS_KEY_ID, env_var=ENV_GV_AWS_ACCESS_KEY_ID)

    def get_aws_secret_access_key(self) -> str | None:
        """Get AWS secret access key from config or environment."""
        return self.get(CONFIG_KEY_AWS_SECRET_ACCESS_KEY, env_var=ENV_GV_AWS_SECRET_ACCESS_KEY)

    def get_aws_bucket_name(self) -> str | None:
        """Get AWS S3 bucket name from config or environment."""
        return self.get(CONFIG_KEY_AWS_STORAGE_BUCKET_NAME, env_var=ENV_GV_AWS_STORAGE_BUCKET_NAME)

    def get_langsmith_api_key(self) -> str | None:
        """Get LangSmith API key from config or environment."""
        return self.get(CONFIG_KEY_LANGSMITH_API_KEY, env_var=ENV_LANGSMITH_API_KEY)

    def get_langsmith_project(self) -> str | None:
        """Get LangSmith project name from config or environment."""
        return self.get(CONFIG_KEY_LANGSMITH_PROJECT, env_var=ENV_LANGSMITH_PROJECT)

    def get_default_model(self) -> str:
        """
        Get default model name (deprecated - use get_generation_model or get_analysis_model).

        This method is deprecated because different tasks require different models.
        Use get_generation_model() for image generation tasks and get_analysis_model()
        for image understanding/analysis tasks.

        Returns:
            Default model name
        """
        return self.get(CONFIG_KEY_DEFAULT_MODEL, default=DEFAULT_GENERATION_MODEL)

    def get_generation_model(self) -> str:
        """
        Get model for image generation tasks.

        Image generation requires models that support image output modalities.
        This method checks in order:
        1. generation_model config value
        2. default_model config value
        3. Hardcoded default from constants.DEFAULT_GENERATION_MODEL

        Returns:
            Model name to use for image generation
        """
        # Try generation_model first, then default_model, then hardcoded default
        return self.get("generation_model") or self.get(
            CONFIG_KEY_DEFAULT_MODEL, default=DEFAULT_GENERATION_MODEL
        )

    def get_analysis_model(self) -> str:
        """
        Get model for image analysis/understanding tasks.

        Image analysis typically uses faster, text-output models that can
        efficiently process and describe images. This method checks in order:
        1. analysis_model config value
        2. default_model config value
        3. Hardcoded default from constants.DEFAULT_ANALYSIS_MODEL

        Returns:
            Model name to use for image analysis
        """
        # Try analysis_model first, then default_model, then hardcoded default
        return self.get("analysis_model") or self.get(
            CONFIG_KEY_DEFAULT_MODEL, default=DEFAULT_ANALYSIS_MODEL
        )

    def get_langsmith_tracing(self) -> bool:
        """Get LangSmith tracing enabled status."""
        value = self.get(CONFIG_KEY_LANGSMITH_TRACING, default=False, env_var=ENV_LANGSMITH_TRACING)
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def get_temperature(self) -> float | None:
        """Get default temperature from config."""
        return self.get(CONFIG_KEY_TEMPERATURE)

    def get_aspect_ratio(self) -> str | None:
        """Get default aspect ratio from config."""
        return self.get(CONFIG_KEY_ASPECT_RATIO)

    def get_safety_settings(self) -> list[dict[str, Any]] | None:
        """
        Get default safety settings from config.

        Returns a list of dicts with 'category' and 'threshold' keys
        that can be converted to SafetySetting objects.
        """
        return self.get(CONFIG_KEY_SAFETY_SETTINGS)


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
