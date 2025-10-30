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

    @patch("gemini_imagen.s3_utils.get_s3_client")
    @patch("gemini_imagen.s3_utils.get_http_url")
    def test_upload_to_s3(self, mock_get_url, mock_get_client, tmp_path, sample_image):
        """Test uploading file to S3."""
        # Create a test file
        test_file = tmp_path / "test.png"
        sample_image.save(test_file)

        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        mock_get_url.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/path/test.png"

        # Test upload - API is upload_to_s3(local_path, s3_key, bucket, region)
        s3_uri, http_url = upload_to_s3(str(test_file), "path/test.png", "test-bucket")

        # Verify S3 client was called correctly
        mock_s3.put_object.assert_called_once()
        assert s3_uri == "s3://test-bucket/path/test.png"
        assert http_url == "https://test-bucket.s3.us-east-1.amazonaws.com/path/test.png"

    @patch("gemini_imagen.s3_utils.get_s3_client")
    @patch("gemini_imagen.s3_utils.parse_s3_uri")
    @patch("PIL.Image.open")
    def test_download_from_s3(self, mock_image_open, mock_parse, mock_get_client, tmp_path, sample_image):
        """Test downloading file from S3."""
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        mock_parse.return_value = ("test-bucket", "path/file.png")
        mock_image_open.return_value = sample_image

        # Mock S3 download response
        mock_s3.download_fileobj.return_value = None

        # Test download - API is download_from_s3(s3_uri, local_path=None)
        result = download_from_s3("s3://test-bucket/path/file.png")

        # Verify it returns a PIL Image
        assert isinstance(result, Image.Image)

    def test_get_http_url(self):
        """Test generating HTTP URL from bucket and key."""
        # API is get_http_url(bucket, key, region="us-east-1")
        url = get_http_url("my-bucket", "path/to/file.png", "us-east-1")

        assert url == "https://my-bucket.s3.us-east-1.amazonaws.com/path/to/file.png"


class TestImageOperations:
    """Test image load/save operations."""

    def test_load_local_image(self, sample_image_path):
        """Test loading image from local path."""
        # API returns just Image.Image
        img = load_image(str(sample_image_path))
        assert isinstance(img, Image.Image)

    def test_load_pil_image(self, sample_image):
        """Test loading PIL Image object."""
        # API returns just Image.Image
        img = load_image(sample_image)
        assert img == sample_image

    @patch("gemini_imagen.s3_utils.download_from_s3")
    def test_load_s3_image(self, mock_download, tmp_path, sample_image):
        """Test loading image from S3."""
        # Mock download_from_s3 to return a PIL Image
        mock_download.return_value = sample_image

        img = load_image("s3://test-bucket/image.png")

        assert isinstance(img, Image.Image)
        mock_download.assert_called_once_with("s3://test-bucket/image.png")

    def test_save_local_image(self, sample_image, tmp_path):
        """Test saving image to local path."""
        output_path = tmp_path / "output.png"
        # API returns (location, s3_uri, http_url)
        location, s3_uri, http_url = save_image(sample_image, str(output_path))

        assert location == str(output_path)
        assert s3_uri is None
        assert http_url is None
        assert output_path.exists()

    @patch("gemini_imagen.s3_utils.upload_to_s3")
    def test_save_s3_image(self, mock_upload, sample_image, tmp_path):
        """Test saving image to S3."""
        # Mock upload_to_s3 to return (s3_uri, http_url)
        mock_upload.return_value = (
            "s3://test-bucket/test.png",
            "https://test-bucket.s3.us-east-1.amazonaws.com/test.png"
        )

        location, s3_uri, http_url = save_image(sample_image, "s3://test-bucket/test.png")

        assert s3_uri == "s3://test-bucket/test.png"
        assert http_url == "https://test-bucket.s3.us-east-1.amazonaws.com/test.png"
        mock_upload.assert_called_once()
