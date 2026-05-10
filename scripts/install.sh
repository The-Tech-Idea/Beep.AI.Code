#!/usr/bin/env bash
# Beep.AI.Code installer
# Usage: curl -fsSL https://raw.githubusercontent.com/The-Tech-Idea/Beep.AI.Code/master/scripts/install.sh | bash
set -euo pipefail

REPO="The-Tech-Idea/Beep.AI.Code"
BINARY="beep"
INSTALL_DIR="${BEEP_INSTALL_DIR:-}"

_info()  { printf '\033[0;34m[beep]\033[0m %s\n' "$*"; }
_ok()    { printf '\033[0;32m[beep]\033[0m %s\n' "$*"; }
_error() { printf '\033[0;31m[beep]\033[0m %s\n' "$*" >&2; }

# Detect OS
OS="$(uname -s)"
case "$OS" in
  Linux)  OS="linux"  ;;
  Darwin) OS="darwin" ;;
  *)      _error "Unsupported operating system: $OS"; exit 1 ;;
esac

# Detect architecture
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64)   ARCH="x86_64"  ;;
  aarch64|arm64)  ARCH="aarch64" ;;
  *)              _error "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Resolve install directory
if [ -z "$INSTALL_DIR" ]; then
  if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
  else
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
  fi
fi

# Fetch latest release version from GitHub
_info "Fetching latest release..."
if command -v curl &>/dev/null; then
  VERSION=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | grep '"tag_name"' | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')
elif command -v wget &>/dev/null; then
  VERSION=$(wget -qO- "https://api.github.com/repos/$REPO/releases/latest" \
    | grep '"tag_name"' | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')
else
  _error "curl or wget is required"; exit 1
fi

if [ -z "$VERSION" ]; then
  _error "Could not determine the latest release version."; exit 1
fi

ASSET="beep-${OS}-${ARCH}"
URL="https://github.com/$REPO/releases/download/$VERSION/$ASSET"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

_info "Downloading $ASSET $VERSION..."
if command -v curl &>/dev/null; then
  curl -fsSL --progress-bar "$URL" -o "$TMP/$BINARY"
else
  wget -q --show-progress "$URL" -O "$TMP/$BINARY"
fi

chmod +x "$TMP/$BINARY"

# Verify the binary works
if ! "$TMP/$BINARY" --version &>/dev/null; then
  _error "Downloaded binary failed a smoke-test. Please report this at https://github.com/$REPO/issues"
  exit 1
fi

# Install
if [ -w "$INSTALL_DIR" ]; then
  mv "$TMP/$BINARY" "$INSTALL_DIR/$BINARY"
else
  _info "Requesting sudo to install to $INSTALL_DIR..."
  sudo mv "$TMP/$BINARY" "$INSTALL_DIR/$BINARY"
fi

_ok "Installed beep $VERSION to $INSTALL_DIR/$BINARY"

# PATH reminder
if ! command -v beep &>/dev/null; then
  _info "Add $INSTALL_DIR to your PATH if it is not already:"
  _info "  echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> ~/.bashrc  # or ~/.zshrc"
fi
