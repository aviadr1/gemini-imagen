"""
Job merging utility for template + keys system.

Handles deep merging of dictionaries with proper precedence.
"""

import logging
from copy import deepcopy
from typing import Any

logger = logging.getLogger(__name__)


def deep_merge(base: dict[str, Any], *overlays: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge multiple dictionaries with later ones taking precedence.

    Args:
        base: Base dictionary
        *overlays: One or more dictionaries to merge on top of base

    Returns:
        Merged dictionary

    Examples:
        >>> deep_merge({"a": 1}, {"b": 2})
        {'a': 1, 'b': 2}
        >>> deep_merge({"a": 1}, {"a": 2})
        {'a': 2}
        >>> deep_merge({"a": {"b": 1}}, {"a": {"c": 2}})
        {'a': {'b': 1, 'c': 2}}
    """
    logger.debug(f"Deep merging base dict with {len(overlays)} overlay(s)")

    # Start with a deep copy of base to avoid mutations
    result = deepcopy(base)

    for i, overlay in enumerate(overlays):
        logger.debug(f"Merging overlay {i + 1}/{len(overlays)} with {len(overlay)} keys")
        result = _merge_two_dicts(result, overlay)

    logger.info(f"Merge complete: result has {len(result)} top-level keys")
    return result


def _merge_two_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """
    Merge two dictionaries deeply.

    Args:
        base: Base dictionary
        overlay: Overlay dictionary (takes precedence)

    Returns:
        Merged dictionary
    """
    result = deepcopy(base)

    for key, value in overlay.items():
        if key in result:
            # Key exists in both - check if we need deep merge
            if isinstance(result[key], dict) and isinstance(value, dict):
                # Both are dicts - merge recursively
                result[key] = _merge_two_dicts(result[key], value)
                logger.debug(f"Deep merged dict field '{key}'")
            else:
                # One or both are not dicts - overlay wins
                result[key] = deepcopy(value)
                logger.debug(f"Overwrote field '{key}' with overlay value")
        else:
            # New key from overlay
            result[key] = deepcopy(value)
            logger.debug(f"Added new field '{key}' from overlay")

    return result


# Parameters that the library's generate() method accepts
LIBRARY_PARAMS = {
    "prompt",
    "system_prompt",
    "input_images",
    "output_images",
    "temperature",
    "aspect_ratio",
    "safety_settings",
    "output_text",
    "run_name",
    "metadata",
    "tags",
}


def split_job_and_variables(merged: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Split a merged job dictionary into library parameters and variables.

    Args:
        merged: Merged dictionary containing both library params and variables

    Returns:
        Tuple of (library_params, variables)

    Examples:
        >>> merged = {"prompt": "Hello {name}", "name": "Alice", "temperature": 0.8}
        >>> lib_params, vars = split_job_and_variables(merged)
        >>> lib_params
        {'prompt': 'Hello {name}', 'temperature': 0.8}
        >>> vars
        {'name': 'Alice'}
    """
    logger.debug(f"Splitting merged job with {len(merged)} keys")

    library_params = {k: v for k, v in merged.items() if k in LIBRARY_PARAMS}
    variables = {k: v for k, v in merged.items() if k not in LIBRARY_PARAMS}

    logger.info(f"Split into {len(library_params)} library params and {len(variables)} variables")
    logger.debug(f"Library params: {list(library_params.keys())}")
    logger.debug(f"Variables: {list(variables.keys())}")

    return library_params, variables


def merge_template_keys_overrides(
    template: dict[str, Any] | None = None,
    keys: list[dict[str, Any]] | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Merge template, keys files, and CLI overrides in correct precedence order.

    Precedence (highest to lowest):
    1. CLI overrides
    2. Keys files (later ones override earlier ones)
    3. Template

    Args:
        template: Template dictionary (lowest precedence)
        keys: List of keys dictionaries (middle precedence, later > earlier)
        cli_overrides: CLI override dictionary (highest precedence)

    Returns:
        Merged job dictionary

    Examples:
        >>> template = {"prompt": "Hello", "temperature": 0.5}
        >>> keys = [{"prompt": "Hi there", "tags": ["test"]}]
        >>> cli_overrides = {"temperature": 0.9}
        >>> merge_template_keys_overrides(template, keys, cli_overrides)
        {'prompt': 'Hi there', 'temperature': 0.9, 'tags': ['test']}
    """
    logger.info("Merging template, keys, and CLI overrides")

    # Start with empty or template
    if template is not None:
        logger.debug(f"Starting with template ({len(template)} keys)")
        result = deepcopy(template)
    else:
        logger.debug("No template provided, starting with empty dict")
        result = {}

    # Merge keys files in order
    if keys:
        logger.debug(f"Merging {len(keys)} keys file(s)")
        for i, keys_dict in enumerate(keys):
            logger.debug(f"Merging keys file {i + 1}/{len(keys)} with {len(keys_dict)} keys")
            result = deep_merge(result, keys_dict)
    else:
        logger.debug("No keys files provided")

    # Merge CLI overrides last (highest precedence)
    if cli_overrides:
        logger.debug(f"Merging CLI overrides ({len(cli_overrides)} keys)")
        result = deep_merge(result, cli_overrides)
    else:
        logger.debug("No CLI overrides provided")

    logger.info(f"Final merged job has {len(result)} keys")
    return result
