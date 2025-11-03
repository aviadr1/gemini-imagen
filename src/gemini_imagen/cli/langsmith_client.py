"""
LangSmith API client for fetching traces.

Handles authentication and trace retrieval from LangSmith.
"""

import logging
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from ..constants import ENV_LANGSMITH_API_KEY

logger = logging.getLogger(__name__)


def get_langsmith_api_key() -> str | None:
    """
    Get LangSmith API key from environment.

    Returns:
        API key or None if not set

    Environment Variables:
        LANGSMITH_API_KEY: LangSmith API key
    """
    return os.environ.get(ENV_LANGSMITH_API_KEY)


def parse_trace_url(url: str) -> tuple[str | None, str] | None:
    """
    Parse a LangSmith trace URL to extract project and run ID.

    Args:
        url: LangSmith trace URL

    Returns:
        Tuple of (project_id, run_id) or None if invalid

    Examples:
        >>> url = "https://smith.langchain.com/public/abc123/r/def456"
        >>> parse_trace_url(url)
        ('abc123', 'def456')

        >>> url = "https://smith.langchain.com/o/org/projects/p/proj/r/run123"
        >>> parse_trace_url(url)
        ('proj', 'run123')
    """
    logger.debug(f"Parsing trace URL: {url}")

    # Pattern 1: /public/{project}/r/{run}
    match = re.search(r"/public/([^/]+)/r/([^/?]+)", url)
    if match:
        project_id, run_id = match.groups()
        logger.debug(f"Parsed public URL: project={project_id}, run={run_id}")
        return project_id, run_id

    # Pattern 2: /projects/p/{project}/r/{run}
    match = re.search(r"/projects/p/([^/]+)/r/([^/?]+)", url)
    if match:
        project_id, run_id = match.groups()
        logger.debug(f"Parsed project URL: project={project_id}, run={run_id}")
        return project_id, run_id

    # Pattern 3: Just a run ID
    parsed = urlparse(url)
    if not parsed.scheme:
        # Treat as run ID
        logger.debug(f"Treating as run ID: {url}")
        return None, url

    logger.warning(f"Could not parse trace URL: {url}")
    return None


def fetch_trace(run_id: str, api_key: str | None = None) -> dict[str, Any]:
    """
    Fetch a trace/run from LangSmith by ID.

    Args:
        run_id: Run/trace ID
        api_key: LangSmith API key (uses env var if not provided)

    Returns:
        Trace data dictionary

    Raises:
        ValueError: If API key not provided
        httpx.HTTPError: If API request fails
    """
    if api_key is None:
        api_key = get_langsmith_api_key()

    if not api_key:
        msg = "LangSmith API key not provided. Set LANGSMITH_API_KEY environment variable."
        logger.error(msg)
        raise ValueError(msg)

    logger.info(f"Fetching trace: {run_id}")

    # LangSmith API endpoint
    url = f"https://api.smith.langchain.com/runs/{run_id}"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    logger.debug(f"Making request to: {url}")

    with httpx.Client() as client:
        response = client.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()

    trace_data = response.json()
    logger.info(f"Successfully fetched trace: {run_id}")
    logger.debug(f"Trace has {len(trace_data)} top-level keys")

    return trace_data


def fetch_trace_from_url(url: str, api_key: str | None = None) -> dict[str, Any]:
    """
    Fetch a trace from LangSmith by URL.

    Args:
        url: LangSmith trace URL or run ID
        api_key: LangSmith API key (uses env var if not provided)

    Returns:
        Trace data dictionary

    Raises:
        ValueError: If URL is invalid or API key not provided
        httpx.HTTPError: If API request fails
    """
    logger.info(f"Fetching trace from URL: {url}")

    parsed = parse_trace_url(url)
    if not parsed:
        msg = f"Invalid LangSmith trace URL: {url}"
        logger.error(msg)
        raise ValueError(msg)

    project_id, run_id = parsed

    if project_id:
        logger.debug(f"Extracted project={project_id}, run={run_id}")
    else:
        logger.debug(f"Extracted run={run_id}")

    return fetch_trace(run_id, api_key)


def extract_imagen_params(trace_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract gemini-imagen parameters from a LangSmith trace.

    Looks for inputs, outputs, and metadata that correspond to gemini-imagen
    library parameters.

    Args:
        trace_data: Full LangSmith trace data

    Returns:
        Dictionary of gemini-imagen parameters
    """
    logger.debug("Extracting gemini-imagen parameters from trace")

    params = {}

    # Extract from inputs
    if "inputs" in trace_data:
        inputs = trace_data["inputs"]
        if isinstance(inputs, dict):
            # Common input fields
            if "prompt" in inputs:
                params["prompt"] = inputs["prompt"]
            if "system_prompt" in inputs:
                params["system_prompt"] = inputs["system_prompt"]
            if "input_images" in inputs:
                params["input_images"] = inputs["input_images"]

    # Extract from outputs
    if "outputs" in trace_data:
        outputs = trace_data["outputs"]
        if isinstance(outputs, dict) and "output_images" in outputs:
            params["output_images"] = outputs["output_images"]

    # Extract from metadata
    if "extra" in trace_data:
        extra = trace_data["extra"]
        if isinstance(extra, dict):
            # Check for metadata fields
            metadata = extra.get("metadata", {})
            if isinstance(metadata, dict):
                for key in ["temperature", "aspect_ratio", "model", "output_text"]:
                    if key in metadata:
                        params[key] = metadata[key]

    # Extract tags
    if "tags" in trace_data and isinstance(trace_data["tags"], list):
        params["tags"] = trace_data["tags"]

    logger.info(f"Extracted {len(params)} parameters from trace")

    return params
