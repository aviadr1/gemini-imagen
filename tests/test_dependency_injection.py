"""Tests for dependency injection and environment variable fallbacks."""

from __future__ import annotations

import collections.abc
from typing import TYPE_CHECKING

import pytest

from gemini_imagen import GeminiImageGenerator, s3_utils

if TYPE_CHECKING:
    from collections.abc import Iterable
else:
    Iterable = collections.abc.Iterable


@pytest.fixture
def _clear_env(monkeypatch: pytest.MonkeyPatch):
    """Clear credential-related environment variables before each test."""

    def _clear(keys: Iterable[str] | None = None) -> None:
        keys_to_clear = keys or [
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
            "GV_AWS_ACCESS_KEY_ID",
            "AWS_ACCESS_KEY_ID",
            "GV_AWS_SECRET_ACCESS_KEY",
            "AWS_SECRET_ACCESS_KEY",
            "GV_AWS_STORAGE_BUCKET_NAME",
            "AWS_STORAGE_BUCKET_NAME",
        ]
        for key in keys_to_clear:
            monkeypatch.delenv(key, raising=False)

    _clear()
    return _clear


def test_gemini_generator_uses_explicit_credentials(
    mock_gemini_client, _clear_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direct constructor arguments should override environment variables."""

    monkeypatch.setenv("GOOGLE_API_KEY", "env-google-key")
    monkeypatch.setenv("GV_AWS_ACCESS_KEY_ID", "env-gv-access")
    monkeypatch.setenv("GV_AWS_SECRET_ACCESS_KEY", "env-gv-secret")
    monkeypatch.setenv("GV_AWS_STORAGE_BUCKET_NAME", "env-gv-bucket")

    generator = GeminiImageGenerator(
        api_key="explicit-api-key",
        aws_access_key_id="explicit-access",
        aws_secret_access_key="explicit-secret",
        aws_storage_bucket_name="explicit-bucket",
        aws_region="eu-west-1",
    )

    mock_gemini_client.assert_called_once_with(api_key="explicit-api-key")
    assert generator.aws_access_key_id == "explicit-access"
    assert generator.aws_secret_access_key == "explicit-secret"
    assert generator.aws_storage_bucket_name == "explicit-bucket"
    assert generator.aws_region == "eu-west-1"


def test_gemini_generator_prefers_google_api_key_env(
    mock_gemini_client, _clear_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GOOGLE_API_KEY takes precedence over GEMINI_API_KEY when both are set."""

    monkeypatch.setenv("GOOGLE_API_KEY", "google-env-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-env-key")
    monkeypatch.setenv("GV_AWS_ACCESS_KEY_ID", "gv-access")
    monkeypatch.setenv("GV_AWS_SECRET_ACCESS_KEY", "gv-secret")
    monkeypatch.setenv("GV_AWS_STORAGE_BUCKET_NAME", "gv-bucket")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("AWS_STORAGE_BUCKET_NAME", "aws-bucket")

    generator = GeminiImageGenerator()

    mock_gemini_client.assert_called_once_with(api_key="google-env-key")
    assert generator.aws_access_key_id == "gv-access"
    assert generator.aws_secret_access_key == "gv-secret"
    assert generator.aws_storage_bucket_name == "gv-bucket"


def test_gemini_generator_falls_back_to_gemini_api_key(
    mock_gemini_client, _clear_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If GOOGLE_API_KEY is absent, fall back to GEMINI_API_KEY."""

    monkeypatch.setenv("GEMINI_API_KEY", "gemini-only-key")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("AWS_STORAGE_BUCKET_NAME", "aws-bucket")

    generator = GeminiImageGenerator()

    mock_gemini_client.assert_called_once_with(api_key="gemini-only-key")
    assert generator.aws_access_key_id == "aws-access"
    assert generator.aws_secret_access_key == "aws-secret"
    assert generator.aws_storage_bucket_name == "aws-bucket"


def test_gemini_generator_prefers_gv_aws_env(
    mock_gemini_client, _clear_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GV_AWS_* environment variables should override the standard AWS_* keys."""

    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GV_AWS_ACCESS_KEY_ID", "gv-access")
    monkeypatch.setenv("GV_AWS_SECRET_ACCESS_KEY", "gv-secret")
    monkeypatch.setenv("GV_AWS_STORAGE_BUCKET_NAME", "gv-bucket")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("AWS_STORAGE_BUCKET_NAME", "aws-bucket")

    generator = GeminiImageGenerator()

    assert generator.aws_access_key_id == "gv-access"
    assert generator.aws_secret_access_key == "gv-secret"
    assert generator.aws_storage_bucket_name == "gv-bucket"


def test_gemini_generator_falls_back_to_standard_aws_env(
    mock_gemini_client, _clear_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When GV_AWS_* are missing, fall back to AWS_* variables."""

    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("AWS_STORAGE_BUCKET_NAME", "aws-bucket")

    generator = GeminiImageGenerator()

    assert generator.aws_access_key_id == "aws-access"
    assert generator.aws_secret_access_key == "aws-secret"
    assert generator.aws_storage_bucket_name == "aws-bucket"


def test_gemini_generator_requires_api_key(mock_gemini_client, _clear_env) -> None:
    """Initialization should fail when no API key can be resolved."""

    with pytest.raises(ValueError) as exc_info:
        GeminiImageGenerator()

    mock_gemini_client.assert_not_called()
    assert "No API key found" in str(exc_info.value)


def test_get_default_bucket_prefers_argument(_clear_env, monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit bucket argument should override any environment configuration."""

    monkeypatch.setenv("GV_AWS_STORAGE_BUCKET_NAME", "env-bucket")

    assert s3_utils.get_default_bucket("explicit-bucket") == "explicit-bucket"


def test_get_default_bucket_env_priority(_clear_env, monkeypatch: pytest.MonkeyPatch) -> None:
    """GV_AWS_STORAGE_BUCKET_NAME should be used ahead of AWS_STORAGE_BUCKET_NAME."""

    monkeypatch.setenv("GV_AWS_STORAGE_BUCKET_NAME", "gv-bucket")
    monkeypatch.setenv("AWS_STORAGE_BUCKET_NAME", "aws-bucket")

    assert s3_utils.get_default_bucket() == "gv-bucket"


def test_get_default_bucket_falls_back_to_standard_env(
    _clear_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fall back to AWS_STORAGE_BUCKET_NAME when GV_AWS_STORAGE_BUCKET_NAME is missing."""

    monkeypatch.setenv("AWS_STORAGE_BUCKET_NAME", "aws-bucket")

    assert s3_utils.get_default_bucket() == "aws-bucket"


def test_get_default_bucket_missing_env_raises(_clear_env) -> None:
    """An informative error should be raised when no bucket can be located."""

    with pytest.raises(ValueError) as exc_info:
        s3_utils.get_default_bucket()

    assert "Default S3 bucket not configured" in str(exc_info.value)


def test_get_aws_credentials_prefers_parameters(
    _clear_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direct parameters override environment variables in _get_aws_credentials."""

    monkeypatch.setattr(s3_utils, "HAS_AIOBOTOCORE", True)

    access, secret = s3_utils._get_aws_credentials("param-access", "param-secret")

    assert access == "param-access"
    assert secret == "param-secret"


def test_get_aws_credentials_missing_env_raises(
    _clear_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing credentials should raise a ValueError to highlight configuration issues."""

    monkeypatch.setattr(s3_utils, "HAS_AIOBOTOCORE", True)

    with pytest.raises(ValueError) as exc_info:
        s3_utils._get_aws_credentials()

    assert "AWS credentials not found" in str(exc_info.value)


def test_get_aws_credentials_env_priority(_clear_env, monkeypatch: pytest.MonkeyPatch) -> None:
    """GV_AWS_* variables take precedence over AWS_* in _get_aws_credentials."""

    monkeypatch.setattr(s3_utils, "HAS_AIOBOTOCORE", True)
    monkeypatch.setenv("GV_AWS_ACCESS_KEY_ID", "gv-access")
    monkeypatch.setenv("GV_AWS_SECRET_ACCESS_KEY", "gv-secret")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")

    access, secret = s3_utils._get_aws_credentials()

    assert access == "gv-access"
    assert secret == "gv-secret"


def test_get_aws_credentials_falls_back_to_standard_env(
    _clear_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallback to AWS_* environment variables when GV_AWS_* are absent."""

    monkeypatch.setattr(s3_utils, "HAS_AIOBOTOCORE", True)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")

    access, secret = s3_utils._get_aws_credentials()

    assert access == "aws-access"
    assert secret == "aws-secret"
