#!/usr/bin/env bash
# Build a .deb package from the compiled beep binary.
# Usage: scripts/build_deb.sh <binary_path> <version>
# Example: scripts/build_deb.sh dist/beep-linux-x86_64 0.1.0
set -euo pipefail

BINARY="${1:?Usage: $0 <binary_path> <version>}"
VERSION="${2:?Usage: $0 <binary_path> <version>}"
ARCH="${3:-amd64}"

PKG_DIR="$(mktemp -d)"
trap 'rm -rf "$PKG_DIR"' EXIT

install -d "$PKG_DIR/DEBIAN"
install -d "$PKG_DIR/usr/local/bin"
install -m 0755 "$BINARY" "$PKG_DIR/usr/local/bin/beep"

cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: beep
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: Beep.AI Team <support@beep.ai>
Homepage: https://github.com/The-Tech-Idea/Beep.AI.Code
Description: Terminal-native AI coding assistant
 Beep.AI.Code is a CLI code assistant powered by Beep.AI.Server.
 Supports interactive chat, one-shot prompts, an autonomous agent loop,
 MCP tool integration, and portable agent bundles.
EOF

mkdir -p dist
OUTPUT="dist/beep_${VERSION}_${ARCH}.deb"
dpkg-deb --build "$PKG_DIR" "$OUTPUT"
echo "Built: $OUTPUT"
