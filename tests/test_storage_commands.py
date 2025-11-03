"""
Tests for storage CLI commands (upload/download).

Tests the upload and download commands for S3 storage operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from PIL import Image

from gemini_imagen import s3_utils
from gemini_imagen.cli.commands import storage


class TestUploadCommand:
    """Test 'imagen upload' command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_image(self, tmp_path):
        """Create a temporary test image."""
        image_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(image_path)
        return image_path

    def test_upload_success(self, runner, temp_image, tmp_path):
        """Test successful upload to S3."""
        with (
            patch.object(storage, "get_config") as mock_config,
            patch.object(storage, "upload_to_s3", new_callable=AsyncMock) as mock_upload,
            patch.object(s3_utils, "get_http_url") as mock_http_url,
        ):
            # Mock config
            cfg = MagicMock()
            cfg.get_aws_access_key_id.return_value = "test-key"
            cfg.get_aws_secret_access_key.return_value = "test-secret"
            mock_config.return_value = cfg

            # Mock upload
            mock_upload.return_value = ("s3://bucket/key", "https://bucket.s3.amazonaws.com/key")

            # Mock HTTP URL
            mock_http_url.return_value = "https://bucket.s3.amazonaws.com/key"

            result = runner.invoke(storage.upload, [str(temp_image), "s3://bucket/test.png"])

            assert result.exit_code == 0
            assert "Uploaded test.png" in result.output
            assert "s3://bucket/test.png" in result.output
            mock_upload.assert_called_once()

    def test_upload_source_not_exists(self, runner, tmp_path):
        """Test upload with non-existent source file."""
        non_existent = tmp_path / "nonexistent.png"

        result = runner.invoke(storage.upload, [str(non_existent), "s3://bucket/test.png"])

        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_upload_destination_not_s3(self, runner, temp_image):
        """Test upload with non-S3 destination."""
        result = runner.invoke(storage.upload, [str(temp_image), "/local/path.png"])

        assert result.exit_code == 1
        assert "must be an S3 URI" in result.output

    def test_upload_missing_aws_credentials(self, runner, temp_image):
        """Test upload without AWS credentials configured."""
        with patch.object(storage, "get_config") as mock_config:
            # Mock config with no credentials
            cfg = MagicMock()
            cfg.get_aws_access_key_id.return_value = None
            cfg.get_aws_secret_access_key.return_value = None
            mock_config.return_value = cfg

            result = runner.invoke(storage.upload, [str(temp_image), "s3://bucket/test.png"])

            assert result.exit_code == 1
            assert "AWS credentials not configured" in result.output

    def test_upload_json_output(self, runner, temp_image):
        """Test upload with JSON output."""
        with (
            patch.object(storage, "get_config") as mock_config,
            patch.object(storage, "upload_to_s3", new_callable=AsyncMock) as mock_upload,
            patch.object(s3_utils, "get_http_url") as mock_http_url,
        ):
            # Mock config
            cfg = MagicMock()
            cfg.get_aws_access_key_id.return_value = "test-key"
            cfg.get_aws_secret_access_key.return_value = "test-secret"
            mock_config.return_value = cfg

            # Mock upload
            mock_upload.return_value = ("s3://bucket/key", "https://bucket.s3.amazonaws.com/key")

            # Mock HTTP URL
            mock_http_url.return_value = "https://bucket.s3.amazonaws.com/key"

            result = runner.invoke(
                storage.upload, [str(temp_image), "s3://bucket/test.png", "--json"]
            )

            assert result.exit_code == 0
            assert '"success": true' in result.output
            assert '"bucket": "bucket"' in result.output
            assert '"key": "test.png"' in result.output

    def test_upload_exception_handling(self, runner, temp_image):
        """Test upload with exception during upload."""
        with (
            patch.object(storage, "get_config") as mock_config,
            patch.object(storage, "upload_to_s3", new_callable=AsyncMock) as mock_upload,
        ):
            # Mock config
            cfg = MagicMock()
            cfg.get_aws_access_key_id.return_value = "test-key"
            cfg.get_aws_secret_access_key.return_value = "test-secret"
            mock_config.return_value = cfg

            # Mock upload to raise exception
            mock_upload.side_effect = Exception("Upload failed")

            result = runner.invoke(storage.upload, [str(temp_image), "s3://bucket/test.png"])

            assert result.exit_code == 1
            assert "Upload failed" in result.output


class TestDownloadCommand:
    """Test 'imagen download' command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_download_success(self, runner, tmp_path):
        """Test successful download from S3."""
        dest_path = tmp_path / "downloaded.png"

        with (
            patch.object(storage, "get_config") as mock_config,
            patch.object(storage, "download_from_s3", new_callable=AsyncMock) as mock_download,
        ):
            # Mock config
            cfg = MagicMock()
            cfg.get_aws_access_key_id.return_value = "test-key"
            cfg.get_aws_secret_access_key.return_value = "test-secret"
            mock_config.return_value = cfg

            # Mock download to return a PIL Image
            mock_image = Image.new("RGB", (100, 100), color="blue")
            mock_download.return_value = mock_image

            result = runner.invoke(storage.download, ["s3://bucket/test.png", str(dest_path)])

            assert result.exit_code == 0
            assert "Downloaded to" in result.output
            assert dest_path.exists()
            mock_download.assert_called_once()

    def test_download_source_not_s3(self, runner, tmp_path):
        """Test download with non-S3 source."""
        dest_path = tmp_path / "downloaded.png"

        result = runner.invoke(storage.download, ["/local/path.png", str(dest_path)])

        assert result.exit_code == 1
        assert "must be an S3 URI" in result.output

    def test_download_parent_dir_not_exists(self, runner, tmp_path):
        """Test download with non-existent parent directory."""
        dest_path = tmp_path / "nonexistent" / "subdir" / "downloaded.png"

        result = runner.invoke(storage.download, ["s3://bucket/test.png", str(dest_path)])

        assert result.exit_code == 1
        assert "Parent directory does not exist" in result.output

    def test_download_missing_aws_credentials(self, runner, tmp_path):
        """Test download without AWS credentials configured."""
        dest_path = tmp_path / "downloaded.png"

        with patch.object(storage, "get_config") as mock_config:
            # Mock config with no credentials
            cfg = MagicMock()
            cfg.get_aws_access_key_id.return_value = None
            cfg.get_aws_secret_access_key.return_value = None
            mock_config.return_value = cfg

            result = runner.invoke(storage.download, ["s3://bucket/test.png", str(dest_path)])

            assert result.exit_code == 1
            assert "AWS credentials not configured" in result.output

    def test_download_json_output(self, runner, tmp_path):
        """Test download with JSON output."""
        dest_path = tmp_path / "downloaded.png"

        with (
            patch.object(storage, "get_config") as mock_config,
            patch.object(storage, "download_from_s3", new_callable=AsyncMock) as mock_download,
        ):
            # Mock config
            cfg = MagicMock()
            cfg.get_aws_access_key_id.return_value = "test-key"
            cfg.get_aws_secret_access_key.return_value = "test-secret"
            mock_config.return_value = cfg

            # Mock download to return a PIL Image
            mock_image = Image.new("RGB", (100, 100), color="blue")
            mock_download.return_value = mock_image

            result = runner.invoke(
                storage.download, ["s3://bucket/test.png", str(dest_path), "--json"]
            )

            assert result.exit_code == 0
            assert '"success": true' in result.output
            assert '"bucket": "bucket"' in result.output
            assert '"key": "test.png"' in result.output

    def test_download_exception_handling(self, runner, tmp_path):
        """Test download with exception during download."""
        dest_path = tmp_path / "downloaded.png"

        with (
            patch.object(storage, "get_config") as mock_config,
            patch.object(storage, "download_from_s3", new_callable=AsyncMock) as mock_download,
        ):
            # Mock config
            cfg = MagicMock()
            cfg.get_aws_access_key_id.return_value = "test-key"
            cfg.get_aws_secret_access_key.return_value = "test-secret"
            mock_config.return_value = cfg

            # Mock download to raise exception
            mock_download.side_effect = Exception("Download failed")

            result = runner.invoke(storage.download, ["s3://bucket/test.png", str(dest_path)])

            assert result.exit_code == 1
            assert "Download failed" in result.output
