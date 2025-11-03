"""
LangSmith utilities for extracting templates and keys from traces.

Handles special patterns like triple-backtick variables for structured prompts.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_backtick_sections(text: str) -> dict[str, str]:
    """
    Extract content within triple-backtick sections as potential variables.

    Pattern: ```\n{content}\n```

    Args:
        text: Text containing triple-backtick sections

    Returns:
        Dictionary mapping detected variable names to their content

    Examples:
        >>> text = "# Context\\n```\\n{community_info}\\n```"
        >>> extract_backtick_sections(text)
        {'community_info': '{community_info}'}
    """
    logger.debug("Extracting backtick sections from text")

    # Pattern to match triple backticks with content
    pattern = r"```\s*\n(.*?)\n\s*```"
    matches = re.findall(pattern, text, re.DOTALL)

    logger.debug(f"Found {len(matches)} backtick sections")

    variables = {}
    for i, content in enumerate(matches):
        content = content.strip()

        # Check if this looks like a variable placeholder: {variable_name}
        var_match = re.match(r"^\{(\w+)\}$", content)
        if var_match:
            var_name = var_match.group(1)
            variables[var_name] = content
            logger.debug(f"Detected variable in backticks: {var_name}")
        else:
            # Check if this looks like JSON or structured data
            if content.startswith("{") or content.startswith("["):
                # This might be actual data, not a placeholder
                # Try to detect the variable name from context if possible
                logger.debug(f"Found structured data in backticks (section {i + 1})")

    return variables


def detect_variable_in_context(text: str, backtick_content: str) -> str | None:
    """
    Try to detect what variable name a backtick section should use based on context.

    Looks for patterns like "# Context: The community" before the backtick section.

    Args:
        text: Full text containing the backtick section
        backtick_content: The content within backticks

    Returns:
        Suggested variable name or None

    Examples:
        >>> text = "# Context: The community\\n```\\n{...}\\n```"
        >>> detect_variable_in_context(text, "{...}")
        'community_info'
    """
    # Find the position of this backtick content
    escaped_content = re.escape(backtick_content[:50])  # Use first 50 chars
    pattern = rf"#\s*Context:\s*[Tt]he\s+(\w+).*?```\s*\n{escaped_content}"

    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        context_word = match.group(1).lower()
        var_name = f"{context_word}_info"
        logger.debug(f"Detected variable name from context: {var_name}")
        return var_name

    return None


def split_template_from_trace(trace_data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Split a LangSmith trace into template (structure) and keys (data).

    Args:
        trace_data: Full trace data from LangSmith

    Returns:
        Tuple of (template_dict, keys_dict)

    The template contains:
    - prompt with {variable} placeholders
    - system_prompt with {variable} placeholders
    - output_images patterns with {variable} placeholders
    - Any other structural fields

    The keys contain:
    - Actual values for {variable} placeholders
    - input_images list
    - Other episode-specific data
    """
    logger.info("Splitting LangSmith trace into template and keys")

    template = {}
    keys = {}

    # Get the prompt
    prompt = trace_data.get("prompt", "")

    if prompt:
        # Check if prompt has triple-backtick sections
        if "```" in prompt:
            logger.debug("Prompt contains backtick sections")

            # Extract backtick variables
            backtick_vars = extract_backtick_sections(prompt)

            if backtick_vars:
                # Replace actual data with {variable} placeholders in template
                template_prompt = prompt

                for var_name in backtick_vars:
                    # Find the actual data in the trace for this variable
                    # Look for fields that might match
                    for key, value in trace_data.items():
                        if key.lower().replace("_", "") in var_name.lower().replace(
                            "_", ""
                        ) and isinstance(value, str):
                            # This might be the data for this variable
                            keys[var_name] = value
                            logger.debug(f"Mapped {var_name} to trace field: {key}")

                template["prompt"] = template_prompt
            else:
                template["prompt"] = prompt
        else:
            template["prompt"] = prompt

    # System prompt typically doesn't change
    if "system_prompt" in trace_data:
        template["system_prompt"] = trace_data["system_prompt"]

    # Output images - extract pattern with variables
    if "output_images" in trace_data:
        output_list = trace_data["output_images"]
        if output_list and isinstance(output_list, list):
            # Try to detect variable patterns like {channel_id} in paths
            output_path = output_list[0]
            if isinstance(output_path, str):
                # Look for path components that might be variables
                # e.g., "s3://bucket/thumbnails/drumming2-abc123/thumb.jpg"
                #       -> "s3://bucket/thumbnails/{channel_id}/thumb.jpg"

                # For now, just keep as-is in template
                # More sophisticated pattern detection could be added
                template["output_images"] = output_list

    # Input images go in keys (episode-specific)
    if "input_images" in trace_data:
        keys["input_images"] = trace_data["input_images"]

    # Extract other potential variables from trace
    # Look for fields that end with _info, _data, _context, etc.
    for key, value in trace_data.items():
        if key not in ["prompt", "system_prompt", "output_images", "input_images"]:
            # Check if this looks like variable data
            if any(
                suffix in key.lower()
                for suffix in ["_info", "_data", "_context", "community", "host", "show"]
            ):
                keys[key] = value
                logger.debug(f"Added {key} to keys")
            else:
                # Might be a structural field for template
                if key in ["temperature", "aspect_ratio", "tags", "output_text"]:
                    template[key] = value
                elif isinstance(value, str | int | float | bool | type(None)):
                    # Could be either, but lean towards keys if it's data
                    if isinstance(value, str) and len(value) > 50:
                        keys[key] = value
                    else:
                        template[key] = value

    logger.info(f"Split into template ({len(template)} keys) and keys ({len(keys)} keys)")

    return template, keys


def convert_backtick_data_to_variables(
    prompt: str, data_dict: dict[str, Any]
) -> tuple[str, dict[str, str]]:
    """
    Convert a prompt with actual data in backticks to template with {variables}.

    Args:
        prompt: Prompt with triple-backtick sections containing actual data
        data_dict: Dictionary containing the actual data values

    Returns:
        Tuple of (template_prompt, variables_dict)

    Examples:
        >>> prompt = '''# Community
        ... ```
        ... {"name":"PowerfulJRE"}
        ... ```'''
        >>> data = {"community_info": '{"name":"PowerfulJRE"}'}
        >>> template, vars = convert_backtick_data_to_variables(prompt, data)
        >>> print(template)
        # Community
        ```
        {community_info}
        ```
    """
    logger.debug("Converting backtick data to variables")

    # Find all backtick sections with actual data
    pattern = r"(```\s*\n)(.*?)(\n\s*```)"
    matches = list(re.finditer(pattern, prompt, re.DOTALL))

    logger.debug(f"Found {len(matches)} backtick sections to process")

    template_prompt = prompt
    variables = {}

    # Process each backtick section
    for i, match in enumerate(reversed(matches)):  # Reverse to avoid offset issues
        data_content = match.group(2).strip()

        # Try to find which variable this data belongs to
        var_name = None

        # Try to match with data_dict entries
        for key, value in data_dict.items():
            if isinstance(value, str) and value.replace(" ", "").replace(
                "\n", ""
            ) == data_content.replace(" ", "").replace("\n", ""):
                # Remove whitespace for comparison matched
                var_name = key
                break

        # If we found a match, replace with {variable}
        if var_name:
            replacement = f"{match.group(1)}{{{var_name}}}{match.group(3)}"
            template_prompt = (
                template_prompt[: match.start()] + replacement + template_prompt[match.end() :]
            )
            variables[var_name] = data_content
            logger.debug(f"Replaced backtick section {i + 1} with {{{var_name}}}")
        else:
            # Try to infer variable name from context
            var_name = detect_variable_in_context(prompt, data_content)
            if var_name:
                replacement = f"{match.group(1)}{{{var_name}}}{match.group(3)}"
                template_prompt = (
                    template_prompt[: match.start()] + replacement + template_prompt[match.end() :]
                )
                variables[var_name] = data_content
                logger.debug(f"Inferred and replaced with {{{var_name}}}")

    logger.info(f"Converted prompt to template with {len(variables)} variables")

    return template_prompt, variables
