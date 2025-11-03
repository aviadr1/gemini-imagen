"""
Variable substitution for template system.

Handles extraction and substitution of {variable} placeholders in templates.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_variables(text: str) -> set[str]:
    """
    Extract {variable_name} placeholders from text.

    Args:
        text: Text containing variable placeholders

    Returns:
        Set of variable names found in text

    Examples:
        >>> extract_variables("Hello {name}!")
        {'name'}
        >>> extract_variables("{greeting} {name}, you have {count} messages")
        {'greeting', 'name', 'count'}
    """
    variables = set(re.findall(r"\{(\w+)\}", text))
    logger.debug(f"Extracted {len(variables)} variables from text: {variables}")
    return variables


def find_template_variables(template: dict[str, Any]) -> dict[str, list[str]]:
    """
    Find all variable placeholders used in a template.

    Args:
        template: Template dictionary

    Returns:
        Dictionary mapping field names to lists of variables used in that field

    Examples:
        >>> template = {
        ...     "prompt": "Hello {name}",
        ...     "output_images": ["output_{id}.png"]
        ... }
        >>> find_template_variables(template)
        {'prompt': ['name'], 'output_images': ['id']}
    """
    logger.debug(f"Finding variables in template with keys: {template.keys()}")
    variables_by_field: dict[str, list[str]] = {}

    # Check string fields
    for field in ["prompt", "system_prompt"]:
        if field in template and isinstance(template[field], str):
            vars_found = extract_variables(template[field])
            if vars_found:
                variables_by_field[field] = sorted(vars_found)
                logger.debug(f"Field '{field}' uses variables: {vars_found}")

    # Check list fields (like output_images)
    for field in ["output_images"]:
        if field in template and isinstance(template[field], list):
            all_vars = set()
            for item in template[field]:
                if isinstance(item, str):
                    all_vars.update(extract_variables(item))
            if all_vars:
                variables_by_field[field] = sorted(all_vars)
                logger.debug(f"Field '{field}' uses variables: {all_vars}")

    logger.info(
        f"Template uses {sum(len(v) for v in variables_by_field.values())} variable(s) across {len(variables_by_field)} field(s)"
    )
    return variables_by_field


def substitute_in_string(text: str, variables: dict[str, Any]) -> str:
    """
    Substitute {variable} placeholders in a string.

    Args:
        text: Text with variable placeholders
        variables: Dictionary of variable values

    Returns:
        Text with variables substituted

    Raises:
        KeyError: If a variable is missing from the variables dict
    """
    try:
        result = text.format(**variables)
        logger.debug(f"Substituted variables in string (length {len(text)} -> {len(result)})")
        return result
    except KeyError as e:
        missing_var = str(e).strip("'")
        logger.error(f"Missing variable '{missing_var}' for substitution")
        raise KeyError(f"Missing variable '{missing_var}' required for substitution") from e


def substitute_variables(
    job: dict[str, Any], variables: dict[str, Any], strict: bool = True
) -> dict[str, Any]:
    """
    Substitute {variable} placeholders throughout a job dictionary.

    Args:
        job: Job dictionary with potential variable placeholders
        variables: Dictionary of variable values
        strict: If True, raise error on missing variables. If False, skip substitution.

    Returns:
        Job dictionary with variables substituted

    Raises:
        KeyError: If a required variable is missing (only if strict=True)
    """
    logger.info(f"Substituting variables in job with {len(variables)} variable(s)")
    logger.debug(f"Available variables: {list(variables.keys())}")

    result: dict[str, Any] = {}

    for key, value in job.items():
        if isinstance(value, str):
            # Check if this string contains variables
            if "{" in value:
                try:
                    result[key] = substitute_in_string(value, variables)
                    logger.debug(f"Substituted variables in field '{key}'")
                except KeyError:
                    if strict:
                        raise
                    # In non-strict mode, keep original
                    result[key] = value
                    logger.warning(
                        f"Skipped variable substitution in field '{key}' due to missing variable"
                    )
            else:
                result[key] = value

        elif isinstance(value, list):
            # Substitute in list items
            substituted_list: list[Any] = []
            for item in value:
                if isinstance(item, str) and "{" in item:
                    try:
                        substituted_list.append(substitute_in_string(item, variables))
                    except KeyError:
                        if strict:
                            raise
                        substituted_list.append(item)
                else:
                    substituted_list.append(item)
            result[key] = substituted_list
            if any(isinstance(item, str) and "{" in item for item in value):
                logger.debug(f"Substituted variables in list field '{key}'")

        else:
            # Non-string, non-list values pass through unchanged
            result[key] = value

    logger.info("Variable substitution completed successfully")
    return result


def validate_variables(
    template: dict[str, Any], variables: dict[str, Any]
) -> tuple[bool, list[str]]:
    """
    Validate that all required variables are provided.

    Args:
        template: Template dictionary
        variables: Dictionary of variable values

    Returns:
        Tuple of (is_valid, missing_variables)
    """
    logger.debug("Validating variables against template")

    # Find all variables used in template
    vars_by_field = find_template_variables(template)
    all_required_vars = set()
    for field_vars in vars_by_field.values():
        all_required_vars.update(field_vars)

    # Check which are missing
    provided_vars = set(variables.keys())
    missing_vars = all_required_vars - provided_vars

    if missing_vars:
        logger.warning(f"Missing {len(missing_vars)} required variable(s): {missing_vars}")
        return False, sorted(missing_vars)

    logger.info("All required variables are provided")
    return True, []
