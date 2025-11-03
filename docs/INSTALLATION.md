# Installation Guide

This guide covers all installation methods for gemini-imagen, from the quick standalone installer to advanced development setups.

## Table of Contents

- [Quick Install (Recommended)](#quick-install-recommended)
- [Traditional Installation](#traditional-installation)
- [Self-Update](#self-update)
- [Uninstallation](#uninstallation)
- [Troubleshooting](#troubleshooting)
- [Advanced](#advanced)

## Quick Install (Recommended)

The standalone installer is the easiest way to get started with gemini-imagen. It creates an isolated environment and handles all dependencies automatically.

### Requirements

- **Python 3.12 or later** (the installer will check and guide you if missing)
- Internet connection
- ~200MB disk space

### Linux / macOS

Open a terminal and run:

```bash
curl -sSL https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.sh | sh
```

Or with wget:

```bash
wget -qO- https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.sh | sh
```

The installer will:
1. Check for Python 3.12+
2. Create an isolated virtual environment at `~/.local/share/gemini-imagen`
3. Install gemini-imagen and all dependencies
4. Create a wrapper script at `~/.local/bin/imagen`
5. Optionally add `~/.local/bin` to your PATH

### Windows

Open PowerShell and run:

```powershell
irm https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.ps1 | iex
```

Or the full command:

```powershell
Invoke-RestMethod -Uri https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.ps1 | Invoke-Expression
```

The installer will:
1. Check for Python 3.12+
2. Create an isolated virtual environment at `%LOCALAPPDATA%\gemini-imagen`
3. Install gemini-imagen and all dependencies
4. Create a wrapper script at `%LOCALAPPDATA%\Programs\imagen\imagen.bat`
5. Optionally add to your Windows PATH

### Manual Download and Run

If you prefer not to pipe to shell, you can download and inspect the installer first:

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.py -o install.py
python3 install.py
```

**Windows:**
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.py -OutFile install.py
python install.py
```

### Verify Installation

After installation, verify it works:

```bash
imagen --version
imagen --help
```

You should see the version number and help output.

### Setting Up Your API Key

Before using imagen, you need a Google API key:

1. Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

2. Configure it:

```bash
# Option 1: Environment variable
export GOOGLE_API_KEY="your-api-key-here"

# Option 2: Save in config
imagen keys set google YOUR_API_KEY
```

3. Test it:

```bash
imagen generate "a serene landscape" -o test.png
```

## Traditional Installation

If you prefer traditional pip installation or need more control:

### With pip

**Basic installation:**
```bash
pip install gemini-imagen
```

**With S3 support:**
```bash
pip install gemini-imagen[s3]
```

**Latest from GitHub:**
```bash
pip install git+https://github.com/aviadr1/gemini-imagen.git
```

### With uv (Faster)

```bash
uv pip install gemini-imagen[s3]
```

### With pipx (Isolated)

```bash
pipx install gemini-imagen[s3]
```

### From Source

For development or contributing:

```bash
# Clone repository
git clone https://github.com/aviadr1/gemini-imagen.git
cd gemini-imagen

# Install with uv (recommended)
uv sync --extra dev --extra s3

# Or with pip
pip install -e ".[dev,s3]"
```

### Package Managers

#### Homebrew (macOS/Linux) - Coming Soon

```bash
brew install imagen
```

#### Chocolatey (Windows) - Coming Soon

```powershell
choco install imagen
```

## Self-Update

The standalone installer includes a self-update feature.

### Check for Updates

```bash
imagen self-update --check
```

### Update to Latest Version

```bash
imagen self-update
```

### Update to Specific Version

```bash
imagen self-update --version 0.6.0
```

### Automatic Update Notifications

If installed via standalone installer, imagen checks for updates once per day and notifies you:

```
💡 New version available: 0.7.0 (current: 0.6.0)
   Run 'imagen self-update' to upgrade
```

### Updating pip Installations

If you installed via pip, use pip to update:

```bash
pip install --upgrade gemini-imagen
```

## Uninstallation

### Standalone Installation

If you installed via the standalone installer, use the uninstaller:

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/uninstall.py | python3 -
```

**Windows:**
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/uninstall.py -OutFile uninstall.py
python uninstall.py
```

The uninstaller will:
- Remove the virtual environment
- Remove the wrapper script
- Remove configuration files
- Optionally clean up PATH modifications

### pip Installation

If you installed via pip:

```bash
pip uninstall gemini-imagen
```

### Manual Cleanup

If uninstallation fails, you can manually remove:

**Linux / macOS:**
- Virtual environment: `~/.local/share/gemini-imagen`
- Wrapper script: `~/.local/bin/imagen`
- Configuration: `~/.config/imagen`

**Windows:**
- Virtual environment: `%LOCALAPPDATA%\gemini-imagen`
- Wrapper script: `%LOCALAPPDATA%\Programs\imagen\imagen.bat`
- Configuration: `%LOCALAPPDATA%\imagen`

## Troubleshooting

### Python Not Found

**Error:** `Python 3.12+ is required but not found.`

**Solution:** Install Python 3.12 or later:

- **macOS:** `brew install python@3.12` or download from [python.org](https://www.python.org/downloads/)
- **Linux:** `sudo apt install python3.12` (Ubuntu/Debian) or equivalent
- **Windows:** Download installer from [python.org](https://www.python.org/downloads/) or Microsoft Store

### Permission Denied

**Error:** Permission errors during installation

**Solution:**

**Linux / macOS:**
```bash
# Don't use sudo with the installer!
# If you get permission errors, check directory permissions:
mkdir -p ~/.local/bin ~/.local/share
chmod u+w ~/.local/bin ~/.local/share
```

**Windows:**
Run PowerShell as Administrator if you get permission errors.

### PATH Not Updated

**Error:** `imagen: command not found` after installation

**Solution:**

**Linux / macOS:**
```bash
# Add to your shell profile manually
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or for zsh:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Windows:**
1. Open "Edit environment variables for your account"
2. Add `%LOCALAPPDATA%\Programs\imagen` to your user PATH
3. Restart terminal

### Installer Download Fails

**Error:** `Failed to download installer`

**Solution:**

1. Check internet connection
2. Try direct download:
   ```bash
   # Save to file first
   curl -o install.py https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.py
   python3 install.py
   ```
3. Check if GitHub is accessible from your network

### Self-Update Fails

**Error:** `self-update only works for standalone installations`

**Solution:** You installed via pip. Use pip to update:
```bash
pip install --upgrade gemini-imagen
```

**Error:** `Could not check for updates`

**Solution:**
- Check internet connection
- GitHub API might be rate-limited (wait a bit)
- Manually install latest version: `pip install --upgrade gemini-imagen`

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'gemini_imagen'`

**Solution:**

**Standalone installation:**
- The wrapper script might be broken
- Try reinstalling: Run the installer again

**pip installation:**
```bash
# Reinstall
pip uninstall gemini-imagen
pip install gemini-imagen[s3]
```

### SSL Certificate Errors

**Error:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution:**

**macOS:**
```bash
# Install certificates
/Applications/Python\ 3.12/Install\ Certificates.command
```

**Linux/Windows:**
```bash
# Upgrade certifi
pip install --upgrade certifi
```

## Advanced

### Custom Installation Location

You can customize where the standalone installer places files by setting environment variables:

**Linux / macOS:**
```bash
export XDG_DATA_HOME="$HOME/custom/data"
export XDG_CONFIG_HOME="$HOME/custom/config"
python3 install.py
```

**Windows:**
```powershell
$env:LOCALAPPDATA = "C:\Custom\Path"
python install.py
```

### Offline Installation

For air-gapped systems:

1. Download wheel and dependencies on a connected machine:
   ```bash
   pip download gemini-imagen[s3] -d packages/
   ```

2. Transfer the `packages/` directory to offline machine

3. Install from local packages:
   ```bash
   pip install --no-index --find-links packages/ gemini-imagen[s3]
   ```

### Docker Installation

```dockerfile
FROM python:3.12-slim

RUN pip install gemini-imagen[s3]

ENTRYPOINT ["imagen"]
```

Build and run:
```bash
docker build -t imagen .
docker run --rm -v $(pwd):/work -w /work -e GOOGLE_API_KEY imagen generate "prompt" -o out.png
```

### Development Installation

For contributing to gemini-imagen:

```bash
# Clone and setup
git clone https://github.com/aviadr1/gemini-imagen.git
cd gemini-imagen

# Install with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --extra dev --extra s3

# Run tests
uv run pytest

# Run CLI
uv run imagen --help
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full development setup.

### Multiple Versions

You can install multiple versions side-by-side using virtual environments:

```bash
# Version 0.6.0
python3 -m venv venv-0.6.0
source venv-0.6.0/bin/activate
pip install gemini-imagen==0.6.0

# Version 0.7.0 (separate venv)
python3 -m venv venv-0.7.0
source venv-0.7.0/bin/activate
pip install gemini-imagen==0.7.0
```

### Behind a Proxy

```bash
# Set proxy environment variables
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# Then run installer
curl -sSL https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.sh | sh
```

Or for pip:
```bash
pip install --proxy http://proxy.example.com:8080 gemini-imagen
```

## Getting Help

If you encounter issues not covered here:

1. Check [existing issues](https://github.com/aviadr1/gemini-imagen/issues)
2. Search [discussions](https://github.com/aviadr1/gemini-imagen/discussions)
3. Open a [new issue](https://github.com/aviadr1/gemini-imagen/issues/new) with:
   - Your OS and version
   - Python version (`python --version`)
   - Installation method used
   - Complete error message
   - Steps to reproduce

## Next Steps

After installation:

- **Quick Start:** See [README.md](../README.md#quick-start)
- **CLI Usage:** See [README.md](../README.md#cli-commands)
- **Python Library:** See [LIBRARY.md](../LIBRARY.md)
- **Advanced Features:** See [ADVANCED_USAGE.md](../ADVANCED_USAGE.md)
- **Contributing:** See [CONTRIBUTING.md](../CONTRIBUTING.md)
