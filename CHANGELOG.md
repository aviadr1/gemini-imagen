# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI/CD pipeline with GitHub Actions
- Comprehensive test suite with pytest
- Pre-commit hooks for code quality
- Dependabot for dependency updates
- Issue and PR templates
- Code quality tools (ruff, mypy)

## [0.1.0] - 2025-10-30

### Added
- Initial release
- Text-to-image generation using Google Gemini
- Image analysis with text output
- Labeled input images for better prompt control
- Multiple output images support
- AWS S3 integration for image storage
- LangSmith tracing for observability
- Full type safety with Pydantic validation
- Comprehensive documentation and examples

### Features
- `GeminiImageGenerator` class for easy interaction with Gemini API
- Support for `gemini-2.5-flash-image` model
- Flexible output modalities (IMAGE, TEXT, or both)
- S3 URI support for both input and output images
- HTTP URL generation for S3 objects
- LangSmith integration with metadata and tags
- Type-safe `GenerationResult` with backward-compatible properties

[Unreleased]: https://github.com/aviadr1/gemini-imagen/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/aviadr1/gemini-imagen/releases/tag/v0.1.0
