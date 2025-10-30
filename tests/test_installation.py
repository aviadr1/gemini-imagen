"""
Test that the package can be built and installed from wheel.

This test builds the package, installs it in a fresh virtual environment,
and verifies basic functionality works - simulating a user's experience.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.mark.integration
def test_build_and_install_from_wheel():
    """Test building wheel and installing in fresh venv."""
    project_root = Path(__file__).parent.parent

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Build the wheel
        print("\n📦 Building wheel...")
        build_result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmpdir_path)],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"

        # Find the wheel file
        wheels = list(tmpdir_path.glob("*.whl"))
        assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}"
        wheel_path = wheels[0]
        print(f"✅ Built: {wheel_path.name}")

        # Create fresh venv
        venv_path = tmpdir_path / "test_venv"
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"

        print("\n🔨 Creating fresh virtual environment...")
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
        )

        # Install the wheel
        print(f"📥 Installing {wheel_path.name}...")
        install_result = subprocess.run(
            [str(pip_exe), "install", str(wheel_path)],
            capture_output=True,
            text=True,
        )
        assert install_result.returncode == 0, f"Install failed: {install_result.stderr}"

        # Test basic usage - this simulates what a user would do
        test_script = """
# This is what a user would do after: pip install gemini-imagen
from gemini_imagen import GeminiImageGenerator, GenerationResult
from PIL import Image

# Test 1: Import works
print("✓ Imports work")

# Test 2: Can instantiate generator
gen = GeminiImageGenerator(api_key="test_api_key")
assert gen.model_name == "gemini-2.5-flash-image"
assert gen.log_images == True
print("✓ Can create GeminiImageGenerator")

# Test 3: GenerationResult works
result = GenerationResult()
assert result.text is None
assert result.images == []
print("✓ GenerationResult works")

# Test 4: Check dependencies are available
from google import genai
from google.genai import types
from pydantic import BaseModel
print("✓ Dependencies available")

print("\\n🎉 SUCCESS: Package works as expected for end users!")
"""

        print("\n🧪 Testing user-facing functionality...")
        result = subprocess.run(
            [str(python_exe), "-c", test_script],
            capture_output=True,
            text=True,
        )

        # Print output for debugging
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")

        assert result.returncode == 0, f"User test failed: {result.stderr}"
        assert "SUCCESS" in result.stdout
