"""Tests for edge cases in save_image functionality."""

from pathlib import Path

import pytest
from PIL import Image

from gemini_imagen.s3_utils import save_image


class TestSaveImageEdgeCases:
    """Test edge cases for saving images."""

    @pytest.mark.asyncio
    async def test_save_image_filename_without_directory(self, sample_image, tmp_path):
        """Test saving image with just a filename (no directory path)."""
        # Change to tmp_path to simulate relative path
        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            location, s3_uri, http_url = await save_image(sample_image, "thumbnail.jpg")

            # Should return absolute path even when given relative filename
            assert location == str(tmp_path / "thumbnail.jpg")
            assert Path(location).is_absolute()
            assert s3_uri is None
            assert http_url is None
            assert Path("thumbnail.jpg").exists()
        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_save_image_path_without_extension(self, sample_image, tmp_path):
        """Test that saving without extension raises clear error."""
        output_path = tmp_path / "thumbnail"

        # This should fail with a clear error about missing extension
        with pytest.raises(ValueError, match="unknown file extension"):
            await save_image(sample_image, str(output_path))

    @pytest.mark.asyncio
    async def test_save_image_various_extensions(self, sample_image, tmp_path):
        """Test saving with various image extensions."""
        extensions = [".jpg", ".jpeg", ".png", ".webp"]

        for ext in extensions:
            output_path = tmp_path / f"image{ext}"
            location, _s3_uri, _http_url = await save_image(sample_image, str(output_path))

            assert location == str(output_path)
            assert output_path.exists()

            # Verify the image can be opened
            with Image.open(output_path) as loaded:
                assert loaded.size == sample_image.size

    @pytest.mark.asyncio
    async def test_save_image_creates_parent_directories(self, sample_image, tmp_path):
        """Test that parent directories are created automatically."""
        nested_path = tmp_path / "nested" / "deep" / "directories" / "image.png"

        location, _s3_uri, _http_url = await save_image(sample_image, str(nested_path))

        assert location == str(nested_path)
        assert nested_path.exists()
        assert nested_path.parent.exists()

    @pytest.mark.asyncio
    async def test_save_image_relative_path(self, sample_image, tmp_path):
        """Test saving with relative path."""
        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)

            # Relative path with subdirectory
            relative_path = "output/thumbnail.jpg"
            location, _s3_uri, _http_url = await save_image(sample_image, relative_path)

            # Should return absolute path even when given relative path
            assert Path(relative_path).exists()
            assert location == str(tmp_path / relative_path)
            assert Path(location).is_absolute()
        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_save_image_absolute_path(self, sample_image, tmp_path):
        """Test saving with absolute path."""
        absolute_path = tmp_path / "absolute" / "path" / "image.png"

        location, _s3_uri, _http_url = await save_image(sample_image, str(absolute_path))

        assert location == str(absolute_path)
        assert absolute_path.exists()
        assert absolute_path.is_absolute()

    @pytest.mark.asyncio
    async def test_save_image_special_characters_in_filename(self, sample_image, tmp_path):
        """Test saving with special characters in filename."""
        # Test various special characters that should work
        special_names = [
            "image_with_underscore.jpg",
            "image-with-dash.jpg",
            "image.with.dots.jpg",
            "image (with parens).jpg",
        ]

        for name in special_names:
            output_path = tmp_path / name
            _location, _s3_uri, _http_url = await save_image(sample_image, str(output_path))

            assert output_path.exists()

    @pytest.mark.asyncio
    async def test_save_image_overwrite_existing(self, sample_image, tmp_path):
        """Test that saving overwrites existing file."""
        output_path = tmp_path / "existing.jpg"

        # Create initial file
        sample_image.save(output_path)

        # Save different image
        different_image = Image.new("RGB", (50, 50), color="blue")
        await save_image(different_image, str(output_path))

        # Verify file was overwritten
        assert output_path.exists()
        # At minimum, file should still be readable
        loaded = Image.open(output_path)
        assert loaded.size == (50, 50)


class TestSaveImageFormatDetection:
    """Test PIL format detection edge cases."""

    @pytest.mark.asyncio
    async def test_uppercase_extension(self, sample_image, tmp_path):
        """Test that uppercase extensions work."""
        output_path = tmp_path / "IMAGE.JPG"
        _location, _s3_uri, _http_url = await save_image(sample_image, str(output_path))

        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_mixed_case_extension(self, sample_image, tmp_path):
        """Test that mixed case extensions work."""
        output_path = tmp_path / "image.JpG"
        _location, _s3_uri, _http_url = await save_image(sample_image, str(output_path))

        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_jpeg_vs_jpg_extension(self, sample_image, tmp_path):
        """Test both .jpeg and .jpg extensions work."""
        for ext in [".jpg", ".jpeg"]:
            output_path = tmp_path / f"image{ext}"
            _location, _s3_uri, _http_url = await save_image(sample_image, str(output_path))

            assert output_path.exists()
            loaded = Image.open(output_path)
            assert loaded.format in ["JPEG", "JPG"]


class TestSaveImageErrorMessages:
    """Test that error messages are helpful."""

    @pytest.mark.asyncio
    async def test_empty_path_error(self, sample_image):
        """Test that empty path gives clear error."""
        with pytest.raises((ValueError, OSError)):
            await save_image(sample_image, "")

    @pytest.mark.asyncio
    async def test_invalid_s3_uri_format(self, sample_image):
        """Test that malformed S3 URI gives clear error."""
        # Missing bucket name
        with pytest.raises(ValueError, match="Invalid S3 URI format"):
            await save_image(sample_image, "s3://")

        # Missing key
        with pytest.raises(ValueError, match="Invalid S3 URI format"):
            await save_image(sample_image, "s3://bucket")

    @pytest.mark.asyncio
    async def test_none_path_error(self, sample_image):
        """Test that None path gives clear error."""
        with pytest.raises((TypeError, AttributeError)):
            await save_image(sample_image, None)  # type: ignore
