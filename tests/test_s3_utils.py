"""Tests for S3 utilities."""

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from gemini_imagen.s3_utils import (
    download_from_http,
    download_from_s3,
    get_http_url,
    is_http_url,
    is_s3_uri,
    load_image,
    parse_s3_uri,
    save_image,
    upload_to_s3,
)


class TestUriParsing:
    """Test URI parsing functions."""

    def test_is_s3_uri_valid(self):
        """Test identifying valid S3 URIs."""
        assert is_s3_uri("s3://bucket/key") is True
        assert is_s3_uri("s3://my-bucket/path/to/file.png") is True

    def test_is_s3_uri_invalid(self):
        """Test identifying invalid S3 URIs."""
        assert is_s3_uri("/local/path/file.png") is False
        assert is_s3_uri("https://example.com/file.png") is False
        assert is_s3_uri("file.png") is False

    def test_is_http_url_valid(self):
        """Test identifying valid HTTP(S) URLs."""
        assert is_http_url("http://example.com/image.png") is True
        assert is_http_url("https://example.com/image.png") is True
        assert is_http_url("https://cdn.example.com/path/to/image.jpg") is True

    def test_is_http_url_invalid(self):
        """Test identifying invalid HTTP URLs."""
        assert is_http_url("/local/path/file.png") is False
        assert is_http_url("s3://bucket/key") is False
        assert is_http_url("file.png") is False

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

    @pytest.mark.asyncio
    @patch("gemini_imagen.s3_utils._get_aws_credentials")
    @patch("gemini_imagen.s3_utils.get_session")
    @patch("gemini_imagen.s3_utils.get_http_url")
    async def test_upload_to_s3(
        self, mock_get_url, mock_get_session_func, mock_get_creds, tmp_path, sample_image
    ):
        """Test uploading file to S3."""
        from unittest.mock import AsyncMock

        # Create a test file
        test_file = tmp_path / "test.png"
        sample_image.save(test_file)

        # Mock credentials
        mock_get_creds.return_value = ("fake-key", "fake-secret")

        # Create async mock for S3 client
        mock_s3_client = MagicMock()
        mock_s3_client.put_object = AsyncMock(return_value=None)

        # Create async context manager for client
        mock_client_context = MagicMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=None)

        # Setup session
        mock_session = MagicMock()
        mock_session.create_client = MagicMock(return_value=mock_client_context)
        mock_get_session_func.return_value = mock_session
        mock_get_url.return_value = "https://test-bucket.s3.us-east-1.amazonaws.com/path/test.png"

        # Test upload - API is upload_to_s3(local_path, s3_key, bucket, region)
        s3_uri, http_url = await upload_to_s3(str(test_file), "path/test.png", "test-bucket")

        # Verify S3 URI and HTTP URL
        assert s3_uri == "s3://test-bucket/path/test.png"
        assert http_url == "https://test-bucket.s3.us-east-1.amazonaws.com/path/test.png"

    @pytest.mark.asyncio
    @patch("gemini_imagen.s3_utils._get_aws_credentials")
    @patch("gemini_imagen.s3_utils.get_session")
    @patch("gemini_imagen.s3_utils.parse_s3_uri")
    @patch("PIL.Image.open")
    async def test_download_from_s3(
        self,
        mock_image_open,
        mock_parse,
        mock_get_session_func,
        mock_get_creds,
        tmp_path,
        sample_image,
    ):
        """Test downloading file from S3."""
        from unittest.mock import AsyncMock

        # Mock credentials
        mock_get_creds.return_value = ("fake-key", "fake-secret")

        # Mock the S3 response stream
        mock_stream = MagicMock()
        mock_stream.read = AsyncMock(return_value=b"fake_image_data")
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_response = {"Body": mock_stream}

        # Create async mock for S3 client
        mock_s3_client = MagicMock()
        mock_s3_client.get_object = AsyncMock(return_value=mock_response)

        # Create async context manager for client
        mock_client_context = MagicMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=None)

        # Setup session
        mock_session = MagicMock()
        mock_session.create_client = MagicMock(return_value=mock_client_context)
        mock_get_session_func.return_value = mock_session

        mock_parse.return_value = ("test-bucket", "path/file.png")
        mock_image_open.return_value = sample_image

        # Test download - API is download_from_s3(s3_uri, local_path=None)
        result = await download_from_s3("s3://test-bucket/path/file.png")

        # Verify it returns a PIL Image
        assert isinstance(result, Image.Image)

    def test_get_http_url(self):
        """Test generating HTTP URL from bucket and key."""
        # API is get_http_url(bucket, key, region="us-east-1")
        url = get_http_url("my-bucket", "path/to/file.png", "us-east-1")

        assert url == "https://my-bucket.s3.us-east-1.amazonaws.com/path/to/file.png"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_download_from_http(self, mock_session_class, sample_image):
        """Test downloading image from HTTP URL."""
        from io import BytesIO
        from unittest.mock import AsyncMock

        # Mock image data
        img_buffer = BytesIO()
        sample_image.save(img_buffer, format="PNG")
        image_bytes = img_buffer.getvalue()

        # Create async mock for response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=image_bytes)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Create async mock for session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        # Test download
        result = await download_from_http("https://example.com/image.png")

        assert isinstance(result, Image.Image)


class TestImageOperations:
    """Test image load/save operations."""

    @pytest.mark.asyncio
    async def test_load_local_image(self, sample_image_path):
        """Test loading image from local path."""
        # API returns just Image.Image
        img = await load_image(str(sample_image_path))
        assert isinstance(img, Image.Image)

    @pytest.mark.asyncio
    async def test_load_pil_image(self, sample_image):
        """Test loading PIL Image object."""
        # API returns just Image.Image
        img = await load_image(sample_image)
        assert img == sample_image

    @pytest.mark.asyncio
    @patch("gemini_imagen.s3_utils.download_from_s3")
    async def test_load_s3_image(self, mock_download, tmp_path, sample_image):
        """Test loading image from S3."""
        # Mock download_from_s3 to return a PIL Image (using async mock)
        from unittest.mock import AsyncMock

        mock_download.return_value = sample_image
        mock_download.side_effect = AsyncMock(return_value=sample_image)

        img = await load_image("s3://test-bucket/image.png")

        assert isinstance(img, Image.Image)
        mock_download.assert_called_once_with(
            "s3://test-bucket/image.png", access_key_id=None, secret_access_key=None
        )

    @pytest.mark.asyncio
    @patch("gemini_imagen.s3_utils.download_from_http")
    async def test_load_http_image(self, mock_download, sample_image):
        """Test loading image from HTTP URL."""
        # Mock download_from_http to return a PIL Image (using async mock)
        from unittest.mock import AsyncMock

        mock_download.return_value = sample_image
        mock_download.side_effect = AsyncMock(return_value=sample_image)

        img = await load_image("https://example.com/image.png")

        assert isinstance(img, Image.Image)
        mock_download.assert_called_once_with("https://example.com/image.png")

    @pytest.mark.asyncio
    async def test_save_local_image(self, sample_image, tmp_path):
        """Test saving image to local path."""
        output_path = tmp_path / "output.png"
        # API returns (location, s3_uri, http_url)
        location, s3_uri, http_url = await save_image(sample_image, str(output_path))

        assert location == str(output_path)
        assert s3_uri is None
        assert http_url is None
        assert output_path.exists()

    @pytest.mark.asyncio
    @patch("gemini_imagen.s3_utils.upload_to_s3")
    async def test_save_s3_image(self, mock_upload, sample_image, tmp_path):
        """Test saving image to S3."""
        # Mock upload_to_s3 to return (s3_uri, http_url) (using async mock)
        from unittest.mock import AsyncMock

        mock_upload.return_value = (
            "s3://test-bucket/test.png",
            "https://test-bucket.s3.us-east-1.amazonaws.com/test.png",
        )
        mock_upload.side_effect = AsyncMock(
            return_value=(
                "s3://test-bucket/test.png",
                "https://test-bucket.s3.us-east-1.amazonaws.com/test.png",
            )
        )

        _location, s3_uri, http_url = await save_image(sample_image, "s3://test-bucket/test.png")

        assert s3_uri == "s3://test-bucket/test.png"
        assert http_url == "https://test-bucket.s3.us-east-1.amazonaws.com/test.png"
        mock_upload.assert_called_once()
