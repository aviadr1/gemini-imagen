"""Tests for S3 utilities."""

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from gemini_imagen.s3_utils import (
    download_from_s3,
    get_http_url,
    is_s3_uri,
    load_image,
    parse_s3_uri,
    save_image,
    upload_to_s3,
)


class TestS3UriParsing:
    """Test S3 URI parsing functions."""

    def test_is_s3_uri_valid(self):
        """Test identifying valid S3 URIs."""
        assert is_s3_uri("s3://bucket/key") is True
        assert is_s3_uri("s3://my-bucket/path/to/file.png") is True

    def test_is_s3_uri_invalid(self):
        """Test identifying invalid S3 URIs."""
        assert is_s3_uri("/local/path/file.png") is False
        assert is_s3_uri("https://example.com/file.png") is False
        assert is_s3_uri("file.png") is False

    def test_parse_s3_uri_valid(self):
        """Test parsing valid S3 URIs."""
        bucket, key = parse_s3_uri("s3://my-bucket/path/to/file.png")
        assert bucket == "my-bucket"
        assert key == "path/to/file.png"

    def test_parse_s3_uri_invalid(self):
        """Test parsing invalid S3 URIs raises error."""
        with pytest.raises(ValueError):
            parse_s3_uri("/local/path/file.png")


class TestS3Operations:
    """Test S3 upload/download operations."""

    @patch("gemini_imagen.s3_utils.boto3.client")
    def test_upload_to_s3(self, mock_boto_client, tmp_path, sample_image):
        """Test uploading file to S3."""
        # Create a test file
        test_file = tmp_path / "test.png"
        sample_image.save(test_file)

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Test upload
        upload_to_s3(str(test_file), "test-bucket", "path/test.png")

        # Verify S3 client was called correctly
        mock_s3.upload_file.assert_called_once()
        assert mock_s3.upload_file.call_args[0][0] == str(test_file)
        assert mock_s3.upload_file.call_args[0][1] == "test-bucket"
        assert mock_s3.upload_file.call_args[0][2] == "path/test.png"

    @patch("gemini_imagen.s3_utils.boto3.client")
    def test_download_from_s3(self, mock_boto_client, tmp_path):
        """Test downloading file from S3."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        dest_file = tmp_path / "downloaded.png"

        # Test download
        download_from_s3("test-bucket", "path/file.png", str(dest_file))

        # Verify S3 client was called correctly
        mock_s3.download_file.assert_called_once_with(
            "test-bucket",
            "path/file.png",
            str(dest_file)
        )

    @patch("gemini_imagen.s3_utils.boto3.client")
    def test_get_http_url(self, mock_boto_client):
        """Test generating HTTP URL from S3 URI."""
        mock_s3 = MagicMock()
        mock_s3.meta.region_name = "us-east-1"
        mock_boto_client.return_value = mock_s3

        url = get_http_url("s3://my-bucket/path/to/file.png")

        assert url == "https://my-bucket.s3.us-east-1.amazonaws.com/path/to/file.png"


class TestImageOperations:
    """Test image load/save operations."""

    def test_load_local_image(self, sample_image_path):
        """Test loading image from local path."""
        img, img_type = load_image(str(sample_image_path))
        assert isinstance(img, Image.Image)
        assert img_type == "local"

    def test_load_pil_image(self, sample_image):
        """Test loading PIL Image object."""
        img, img_type = load_image(sample_image)
        assert img == sample_image
        assert img_type == "pil"

    @patch("gemini_imagen.s3_utils.download_from_s3")
    def test_load_s3_image(self, mock_download, tmp_path, sample_image):
        """Test loading image from S3."""
        # Create a temporary image that will be "downloaded"
        temp_img = tmp_path / "temp.png"
        sample_image.save(temp_img)

        def mock_download_side_effect(bucket, key, local_path):
            sample_image.save(local_path)

        mock_download.side_effect = mock_download_side_effect

        img, img_type = load_image("s3://test-bucket/image.png")

        assert isinstance(img, Image.Image)
        assert img_type == "s3"
        mock_download.assert_called_once()

    def test_save_local_image(self, sample_image, tmp_path):
        """Test saving image to local path."""
        output_path = tmp_path / "output.png"
        location, s3_uri = save_image(sample_image, str(output_path))

        assert location == str(output_path)
        assert s3_uri is None
        assert output_path.exists()

    @patch("gemini_imagen.s3_utils.upload_to_s3")
    @patch("gemini_imagen.s3_utils.get_http_url")
    def test_save_s3_image(self, mock_get_url, mock_upload, sample_image, tmp_path):
        """Test saving image to S3."""
        mock_get_url.return_value = "https://bucket.s3.region.amazonaws.com/test.png"

        location, s3_uri = save_image(sample_image, "s3://test-bucket/test.png")

        assert location.startswith("/tmp")  # Temp file
        assert s3_uri == "s3://test-bucket/test.png"
        mock_upload.assert_called_once()
