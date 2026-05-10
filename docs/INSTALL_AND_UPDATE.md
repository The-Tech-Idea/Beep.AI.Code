# Beep.AI.Code — Installation & Update Guide

This guide covers every supported install channel for **end users** and every workflow a **developer** needs to build, test, distribute, and update Beep.AI.Code.

---

## Table of Contents

### For Users
1. [Requirements](#1-requirements)
2. [Install: one-line shell installer (Linux / macOS)](#2-install-one-line-shell-installer-linux--macos)
3. [Install: PowerShell one-liner (Windows)](#3-install-powershell-one-liner-windows)
4. [Install: npm / bun / pnpm](#4-install-npm--bun--pnpm)
5. [Install: Homebrew (macOS / Linux)](#5-install-homebrew-macos--linux)
6. [Install: pip (Python package)](#6-install-pip-python-package)
7. [Install: Linux system packages (.deb / .rpm)](#7-install-linux-system-packages-deb--rpm)
8. [First-run configuration](#8-first-run-configuration)
9. [Updating](#9-updating)
10. [Uninstalling](#10-uninstalling)
11. [Troubleshooting](#11-troubleshooting)

### For Developers
12. [Prerequisites](#12-prerequisites)
13. [Clone and set up the dev environment](#13-clone-and-set-up-the-dev-environment)
14. [Run from source](#14-run-from-source)
15. [Run tests](#15-run-tests)
16. [Versioning](#16-versioning)
17. [Build a self-contained binary locally](#17-build-a-self-contained-binary-locally)
18. [Build Linux packages locally](#18-build-linux-packages-locally)
19. [Publish a release](#19-publish-a-release)
20. [Update the Homebrew formula after a release](#20-update-the-homebrew-formula-after-a-release)
21. [Update the npm package version](#21-update-the-npm-package-version)
22. [Keeping forks / private installs up to date](#22-keeping-forks--private-installs-up-to-date)

---

## For Users

### 1. Requirements

| Channel | Runtime needed on your machine |
|---------|-------------------------------|
| Shell / PowerShell installer | Nothing — downloads a self-contained binary |
| npm | Node.js ≥ 18 |
| Homebrew | Homebrew ≥ 4.0 |
| pip | Python ≥ 3.11 |
| .deb / .rpm | Compatible Linux distro |

All binary channels (shell, PowerShell, npm, Homebrew, .deb, .rpm) download a single self-contained executable — Python is **not** required at runtime.

---

### 2. Install: one-line shell installer (Linux / macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/The-Tech-Idea/Beep.AI.Code/master/scripts/install.sh | bash
```

**What it does:**
1. Detects your OS (`linux` or `darwin`) and CPU arch (`x86_64` or `aarch64`).
2. Queries the GitHub Releases API to find the latest tag.
3. Downloads the matching binary from the release assets.
4. Installs to `/usr/local/bin/beep` (writable) or `~/.local/bin/beep` (fallback).
5. Runs a smoke-test (`beep --version`) before committing the install.

**Options (environment variables):**

```bash
# Install to a custom directory
BEEP_INSTALL_DIR=~/bin curl -fsSL .../install.sh | bash

# Install a specific version
BEEP_VERSION=v0.2.0 curl -fsSL .../install.sh | bash
```

**PATH note:** If the installer chose `~/.local/bin`, make sure it is on your `$PATH`. Add to `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload: `source ~/.bashrc` (or open a new terminal).

---

### 3. Install: PowerShell one-liner (Windows)

Open **PowerShell** (or Windows Terminal) and run:

```powershell
irm https://raw.githubusercontent.com/The-Tech-Idea/Beep.AI.Code/master/scripts/install.ps1 | iex
```

**What it does:**
1. Detects CPU architecture (`x86_64` or `aarch64`).
2. Queries GitHub Releases for the latest version.
3. Downloads `beep-windows-x86_64.exe` (or `aarch64` variant).
4. Installs to `%LOCALAPPDATA%\beep\bin\beep.exe`.
5. Adds that directory to your **user PATH** permanently.
6. Smoke-tests the binary.

**Install to a custom path:**

```powershell
irm .../install.ps1 | iex; Install-Beep -InstallDir "C:\tools\beep"
# or pass directly
powershell -Command "& { $script = irm .../install.ps1; & $script -InstallDir C:\tools\beep }"
```

**Restart your terminal** after install — the PATH change takes effect in new shells only.

---

### 4. Install: npm / bun / pnpm

```bash
# npm
npm install -g beep-ai-code

# bun
bun add -g beep-ai-code

# pnpm
pnpm add -g beep-ai-code
```

The package's `postinstall` script automatically downloads the correct platform binary from GitHub Releases and places it alongside the JS shim. The `beep` command on your PATH will delegate to this binary transparently.

**Requirements:** Node.js ≥ 18 (only needed at install time; the installed binary is standalone).

---

### 5. Install: Homebrew (macOS / Linux)

```bash
# Add the tap once
brew tap the-tech-idea/tap

# Install
brew install the-tech-idea/tap/beep
```

Homebrew installs the correct pre-built binary for your platform and manages your PATH automatically.

After install, Homebrew will print:

```
Run `beep setup` to configure your Beep.AI.Server connection.
```

---

### 6. Install: pip (Python package)

Suitable if you already have Python 3.11+ and want the pure-Python install (source wheel — no compiled binary).

```bash
pip install beep-ai-code
```

**With optional extras:**

```bash
# All extras (JSON schema validation + web search + Semble code search)
pip install "beep-ai-code[all]"

# Individual extras
pip install "beep-ai-code[semble]"      # Semble semantic code search
pip install "beep-ai-code[websearch]"   # Web search context tool
pip install "beep-ai-code[schema]"      # JSON schema validation
```

**Using pipx (isolated, recommended for CLI tools):**

```bash
pipx install beep-ai-code
# or with extras
pipx install "beep-ai-code[all]"
```

---

### 7. Install: Linux system packages (.deb / .rpm)

Pre-built `.deb` and `.rpm` packages are attached to every GitHub Release under [Releases](https://github.com/The-Tech-Idea/Beep.AI.Code/releases).

**Debian / Ubuntu:**

```bash
# Download (replace VERSION with the release tag, e.g. 0.1.0)
curl -LO https://github.com/The-Tech-Idea/Beep.AI.Code/releases/download/vVERSION/beep_VERSION_amd64.deb

# Install
sudo dpkg -i beep_VERSION_amd64.deb
```

**Fedora / RHEL / openSUSE:**

```bash
curl -LO https://github.com/The-Tech-Idea/Beep.AI.Code/releases/download/vVERSION/beep-VERSION-1.x86_64.rpm

sudo rpm -i beep-VERSION-1.x86_64.rpm
# or via dnf
sudo dnf install ./beep-VERSION-1.x86_64.rpm
```

---

### 8. First-run configuration

After any install method, run the interactive setup wizard:

```bash
beep setup
```

The wizard will ask for:
- **Beep.AI.Server URL** — e.g. `http://localhost:5000` or your hosted instance
- **API key** — leave blank if your server does not require authentication
- **Default model** — the inference model to use

Configuration is saved to `~/.beepai/code.json` (permissions `0600` on Unix). You can also set values directly:

```bash
beep config-set agent_base_url http://localhost:5000
beep config-set agent_api_key  sk-...
beep config-set agent_model    gpt-4o
```

**Environment variable overrides** (not persisted, useful for CI):

```bash
export BEEP_AGENT_BASE_URL=http://localhost:5000
export BEEP_AGENT_API_KEY=sk-...
export BEEP_AGENT_MODEL=gpt-4o
beep chat "hello"
```

Verify the configuration:

```bash
beep --version      # confirm the binary version
beep config         # print current effective configuration
beep agent status   # check connectivity to Beep.AI.Server
```

---

### 9. Updating

Each channel has its own upgrade command. **Your configuration in `~/.beepai/code.json` is never touched by an update.**

#### Shell / PowerShell installer

Re-run the same one-liner — the script always fetches the latest release and overwrites the binary in-place:

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/The-Tech-Idea/Beep.AI.Code/master/scripts/install.sh | bash

# Windows PowerShell
irm https://raw.githubusercontent.com/The-Tech-Idea/Beep.AI.Code/master/scripts/install.ps1 | iex
```

To update to a **specific version** instead of latest:

```bash
# Linux / macOS
BEEP_VERSION=v0.3.0 curl -fsSL .../install.sh | bash

# Windows — download that version's asset directly from the Releases page
# and replace %LOCALAPPDATA%\beep\bin\beep.exe
```

#### npm / bun / pnpm

```bash
npm update -g beep-ai-code
# or
npm install -g beep-ai-code@latest

bun add -g beep-ai-code@latest
pnpm update -g beep-ai-code
```

The `postinstall` script runs again and downloads the new binary automatically.

#### Homebrew

```bash
brew upgrade the-tech-idea/tap/beep
```

If the formula is not yet updated for the new version, force a tap refresh first:

```bash
brew tap --force-auto-update the-tech-idea/tap
brew upgrade the-tech-idea/tap/beep
```

#### pip / pipx

```bash
pip install --upgrade beep-ai-code

# pipx
pipx upgrade beep-ai-code
```

#### .deb / .rpm

Download the new package from [Releases](https://github.com/The-Tech-Idea/Beep.AI.Code/releases) and re-install:

```bash
# Debian/Ubuntu — dpkg upgrade (same command)
sudo dpkg -i beep_NEW_VERSION_amd64.deb

# Fedora/RHEL — use upgrade flag
sudo rpm -U beep-NEW_VERSION-1.x86_64.rpm
# or
sudo dnf upgrade ./beep-NEW_VERSION-1.x86_64.rpm
```

---

### 10. Uninstalling

| Channel | How to remove |
|---------|--------------|
| Shell installer (Linux/macOS) | `rm $(which beep)` |
| PowerShell installer (Windows) | `Remove-Item "$env:LOCALAPPDATA\beep" -Recurse -Force` |
| npm | `npm uninstall -g beep-ai-code` |
| Homebrew | `brew uninstall the-tech-idea/tap/beep` |
| pip | `pip uninstall beep-ai-code` |
| pipx | `pipx uninstall beep-ai-code` |
| .deb | `sudo dpkg -r beep` |
| .rpm | `sudo rpm -e beep` |

To also remove your saved configuration:

```bash
rm -rf ~/.beepai
```

---

### 11. Troubleshooting

**`beep: command not found` after install**
- The install directory is not on your `$PATH`.
- For shell installer: check whether `~/.local/bin` is in your PATH (see step 2).
- For Windows: restart your terminal to pick up the PATH change.
- For npm on Windows: run `npm config get prefix` and ensure that `\bin` subdirectory is on your PATH.

**Binary fails with "cannot execute binary file" on Linux/macOS**
- Make sure you downloaded the correct architecture variant (run `uname -m` to check).
- Re-run the installer — it detects architecture automatically.

**SSL/TLS errors on Windows when running the PowerShell installer**
```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
irm .../install.ps1 | iex
```

**`beep agent status` shows connection refused**
- Verify Beep.AI.Server is running at the configured URL.
- Run `beep config` to see the current `agent_base_url`.
- Run `beep agent configure` to re-run the interactive provider setup.

**Check the effective config file location:**
```bash
beep config --show-path
# or directly
cat ~/.beepai/code.json
```

---

## For Developers

### 12. Prerequisites

| Tool | Minimum version | Purpose |
|------|----------------|---------|
| Python | 3.11 | Runtime and tooling |
| uv or pip | latest | Dependency management |
| Git | 2.x | Source control |
| Node.js | 18 | Building the npm wrapper (optional) |
| PyInstaller | 6.x | Building self-contained binaries (optional) |
| Homebrew | 4.x | Testing the formula locally (macOS only, optional) |

---

### 13. Clone and set up the dev environment

```bash
git clone https://github.com/The-Tech-Idea/Beep.AI.Code.git
cd Beep.AI.Code

# Create a virtual environment (Python 3.11+)
python -m venv .venv

# Activate it
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Install in editable mode with all dev + optional extras
pip install -e ".[dev,all]"
```

This puts the `beep` command on your PATH pointing directly at the source tree — every code change takes effect immediately without reinstalling.

---

### 14. Run from source

```bash
# As a module (works without the venv beep script)
python -m beep --help
python -m beep chat "hello"
python -m beep agent status

# Or via the installed editable entry-point
beep --help
```

---

### 15. Run tests

```bash
# All tests
pytest

# With coverage
pytest --cov=beep --cov-report=term-missing

# Specific test file
pytest tests/test_semantic_search_support.py -v

# Specific test pattern
pytest -k "test_coerce" -v

# Fast run skipping slow integration tests (if markers are configured)
pytest -m "not slow" -v
```

Lint and type-check:

```bash
ruff check beep tests
mypy beep
```

The CI matrix (`beep-ai-code-ci.yml`) runs tests on Python 3.11 and 3.12. Run both locally before opening a PR:

```bash
# Quick matrix simulation using pyenv or tox
tox -e py311,py312
```

---

### 16. Versioning

The single source of truth for the version is **`pyproject.toml`**:

```toml
[project]
version = "0.1.0"
```

All other artifacts derive from this:
- `npm/package.json` must be updated to match before a release.
- The GitHub Release tag must be `v<version>` (e.g. `v0.2.0`).
- The Homebrew formula `version` field must also match.

To bump the version across all files, update these three locations in the same commit:

| File | Field |
|------|-------|
| `pyproject.toml` | `version = "..."` |
| `npm/package.json` | `"version": "..."` |
| `Formula/beep.rb` | `version "..."` |

---

### 17. Build a self-contained binary locally

The build uses PyInstaller with the checked-in spec file (`beep.spec`).

```bash
# Make sure PyInstaller and all dependencies are installed
pip install pyinstaller
pip install -e ".[all]"

# Build (output in dist/)
pyinstaller beep.spec --clean --noconfirm

# Smoke-test
./dist/beep --version
```

The binary in `dist/` is completely self-contained — it bundles Python and all dependencies. Copy it anywhere and it works without any Python installation on the target machine.

**Build for a different platform:** Use the GitHub Actions release workflow — each platform is built on a native runner in the matrix. Cross-compilation is not supported for Python binaries.

---

### 18. Build Linux packages locally

Requires `dpkg-deb` (Debian/Ubuntu) and/or `rpmbuild` (Fedora/RHEL).

```bash
# First build the binary (step 17)
pyinstaller beep.spec --clean --noconfirm

# .deb — usage: scripts/build_deb.sh <binary> <version> [arch]
bash scripts/build_deb.sh dist/beep 0.1.0 amd64
# Output: dist/beep_0.1.0_amd64.deb

# .rpm — usage: scripts/build_rpm.sh <binary> <version>
bash scripts/build_rpm.sh dist/beep 0.1.0
# Output: dist/beep-0.1.0-1.x86_64.rpm
```

Install and test locally:

```bash
sudo dpkg -i dist/beep_0.1.0_amd64.deb
beep --version
sudo dpkg -r beep
```

---

### 19. Publish a release

The full release pipeline is automated via `.github/workflows/release.yml`. **Trigger it by pushing a version tag.**

#### Step-by-step

1. **Update the version** in all three files (see [Versioning](#16-versioning)):

   ```bash
   # Edit pyproject.toml, npm/package.json, Formula/beep.rb
   git add pyproject.toml npm/package.json Formula/beep.rb
   git commit -m "chore: bump version to 0.2.0"
   ```

2. **Tag and push:**

   ```bash
   git tag v0.2.0
   git push origin master --tags
   ```

3. **GitHub Actions kicks off automatically.** The release workflow:
   - Builds 5 platform binaries (Linux x86_64, Linux aarch64, macOS arm64, macOS x86_64, Windows x64).
   - Builds `.deb` and `.rpm` packages from the Linux x86_64 binary.
   - Builds the Python wheel and sdist.
   - Creates a GitHub Release and uploads all 9 assets plus `SHA256SUMS.txt`.
   - Publishes to PyPI (`PYPI_TOKEN` secret required).
   - Publishes to npm (`NPM_TOKEN` secret required).

4. **Monitor the workflow** at `https://github.com/The-Tech-Idea/Beep.AI.Code/actions`.

#### Required repository secrets

| Secret | Where used |
|--------|-----------|
| `PYPI_TOKEN` | PyPI publish step |
| `NPM_TOKEN` | npm publish step |
| `GITHUB_TOKEN` | Auto-provided; creates the GitHub Release |

Set these under **Settings → Secrets and variables → Actions** in the repository.

---

### 20. Update the Homebrew formula after a release

After the GitHub Release is published, the Homebrew formula needs the real SHA256 checksums of the new binaries. The `PLACEHOLDER_SHA256_*` values in `Formula/beep.rb` must be replaced.

#### Automated (recommended)

Once GitHub Actions has published the release, run the helper script (you need `shasum` and `curl`):

```bash
VERSION=0.2.0
BASE="https://github.com/The-Tech-Idea/Beep.AI.Code/releases/download/v${VERSION}"

for asset in beep-darwin-aarch64 beep-darwin-x86_64 beep-linux-aarch64 beep-linux-x86_64; do
  echo "${asset}:"
  curl -fsSL "${BASE}/${asset}" | shasum -a 256
done
```

Copy each `sha256` value into `Formula/beep.rb` at the matching `sha256 "..."` line, then also update `version "..."`:

```ruby
version "0.2.0"

on_macos do
  on_arm do
    url "https://...releases/download/v0.2.0/beep-darwin-aarch64"
    sha256 "<real-sha256-here>"
  end
  on_intel do
    url "https://...releases/download/v0.2.0/beep-darwin-x86_64"
    sha256 "<real-sha256-here>"
  end
end
```

Commit and push. Homebrew users then pick up the update with:

```bash
brew update && brew upgrade the-tech-idea/tap/beep
```

#### What is the tap repository?

The formula lives in `Formula/beep.rb` inside **this** repository. The tap is:

```bash
brew tap the-tech-idea/tap https://github.com/The-Tech-Idea/Beep.AI.Code
```

If you move the formula to a dedicated tap repository (`homebrew-tap`), update the URL accordingly.

---

### 21. Update the npm package version

The npm package (`npm/package.json`) is published by the release workflow. For the binary download to resolve correctly:

1. `"version"` in `npm/package.json` must match the release tag (e.g. `"0.2.0"`).
2. `npm/lib/download.js` constructs the GitHub Release URL using the npm package version — no other changes needed.

To verify locally before releasing:

```bash
cd npm
node install.js   # should download the binary for your platform
node bin/beep.js --version
```

---

### 22. Keeping forks / private installs up to date

If you maintain a fork or a private deployment:

**Syncing a fork with upstream:**

```bash
git remote add upstream https://github.com/The-Tech-Idea/Beep.AI.Code.git
git fetch upstream
git merge upstream/master   # or rebase
```

**Installing from a fork's latest commit (edge build):**

```bash
pip install "git+https://github.com/YOUR-ORG/Beep.AI.Code.git"
# with extras
pip install "beep-ai-code[all] @ git+https://github.com/YOUR-ORG/Beep.AI.Code.git"
```

**Private binary distribution:** Run the PyInstaller build (step 17) in CI on your fork and distribute the binary artifact through your own channel. The install scripts accept `BEEP_VERSION` (shell) and the `-InstallDir` parameter (PowerShell) to point at your private release URL if you override the `REPO` variable at the top of the scripts.

---

## File reference

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata and version |
| `beep.spec` | PyInstaller build spec |
| `scripts/install.sh` | curl\|bash installer (Linux/macOS) |
| `scripts/install.ps1` | PowerShell installer (Windows) |
| `scripts/build_deb.sh` | Build `.deb` from binary |
| `scripts/build_rpm.sh` | Build `.rpm` from binary |
| `npm/package.json` | npm package metadata |
| `npm/install.js` | npm postinstall binary downloader |
| `npm/bin/beep.js` | npm shim that delegates to platform binary |
| `Formula/beep.rb` | Homebrew formula |
| `.github/workflows/release.yml` | Full release CI (binaries → GitHub Release → PyPI → npm) |
| `~/.beepai/code.json` | User configuration (created on first run) |
