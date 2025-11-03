"""
Template storage and management.

Handles saving, loading, and managing job templates.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_templates_dir() -> Path:
    """
    Get the templates directory path.

    Returns:
        Path to templates directory

    Examples:
        >>> path = get_templates_dir()
        >>> path.name
        'templates'
    """
    import os

    # Follow XDG Base Directory Specification
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        templates_dir = Path(xdg_config_home) / "imagen" / "templates"
    else:
        templates_dir = Path.home() / ".config" / "imagen" / "templates"

    logger.debug(f"Templates directory: {templates_dir}")
    return templates_dir


def save_template(name: str, template: dict[str, Any]) -> Path:
    """
    Save a template to disk.

    Args:
        name: Template name
        template: Template dictionary

    Returns:
        Path to saved template file

    Raises:
        ValueError: If template name is invalid
    """
    if not name or "/" in name or "\\" in name:
        raise ValueError(f"Invalid template name: {name}")

    templates_dir = get_templates_dir()
    templates_dir.mkdir(parents=True, exist_ok=True)

    template_path = templates_dir / f"{name}.json"

    logger.info(f"Saving template '{name}' to {template_path}")
    logger.debug(f"Template has {len(template)} top-level keys")

    with template_path.open("w") as f:
        json.dump(template, f, indent=2)

    logger.info(f"Template '{name}' saved successfully")
    return template_path


def load_template(name: str) -> dict[str, Any]:
    """
    Load a template from disk.

    Args:
        name: Template name

    Returns:
        Template dictionary

    Raises:
        FileNotFoundError: If template does not exist
        ValueError: If template name is invalid
    """
    if not name or "/" in name or "\\" in name:
        raise ValueError(f"Invalid template name: {name}")

    templates_dir = get_templates_dir()
    template_path = templates_dir / f"{name}.json"

    logger.info(f"Loading template '{name}' from {template_path}")

    if not template_path.exists():
        logger.error(f"Template '{name}' not found at {template_path}")
        raise FileNotFoundError(f"Template '{name}' not found")

    with template_path.open() as f:
        template = json.load(f)

    logger.info(f"Template '{name}' loaded successfully with {len(template)} keys")
    return template


def list_templates() -> list[str]:
    """
    List all available templates.

    Returns:
        List of template names
    """
    templates_dir = get_templates_dir()

    if not templates_dir.exists():
        logger.debug("Templates directory does not exist yet")
        return []

    templates = [path.stem for path in templates_dir.glob("*.json")]

    logger.info(f"Found {len(templates)} template(s)")
    logger.debug(f"Templates: {templates}")

    return sorted(templates)


def delete_template(name: str) -> bool:
    """
    Delete a template.

    Args:
        name: Template name

    Returns:
        True if template was deleted, False if it didn't exist

    Raises:
        ValueError: If template name is invalid
    """
    if not name or "/" in name or "\\" in name:
        raise ValueError(f"Invalid template name: {name}")

    templates_dir = get_templates_dir()
    template_path = templates_dir / f"{name}.json"

    logger.info(f"Deleting template '{name}'")

    if not template_path.exists():
        logger.warning(f"Template '{name}' not found, nothing to delete")
        return False

    template_path.unlink()
    logger.info(f"Template '{name}' deleted successfully")
    return True


def template_exists(name: str) -> bool:
    """
    Check if a template exists.

    Args:
        name: Template name

    Returns:
        True if template exists
    """
    if not name or "/" in name or "\\" in name:
        return False

    templates_dir = get_templates_dir()
    template_path = templates_dir / f"{name}.json"
    exists = template_path.exists()

    logger.debug(f"Template '{name}' exists: {exists}")
    return exists


def get_template_path(name: str) -> Path:
    """
    Get the path to a template file.

    Args:
        name: Template name

    Returns:
        Path to template file (may not exist)

    Raises:
        ValueError: If template name is invalid
    """
    if not name or "/" in name or "\\" in name:
        raise ValueError(f"Invalid template name: {name}")

    templates_dir = get_templates_dir()
    return templates_dir / f"{name}.json"
