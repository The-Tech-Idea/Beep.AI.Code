#!/usr/bin/env bash
# Build an .rpm package from the compiled beep binary.
# Usage: scripts/build_rpm.sh <binary_path> <version>
# Example: scripts/build_rpm.sh dist/beep-linux-x86_64 0.1.0
# Requires: rpmbuild (rpm-build package on Fedora/RHEL/SUSE)
set -euo pipefail

BINARY="${1:?Usage: $0 <binary_path> <version>}"
VERSION="${2:?Usage: $0 <binary_path> <version>}"
RPM_ARCH="${3:-x86_64}"

RPMBUILD_ROOT="$(mktemp -d)"
trap 'rm -rf "$RPMBUILD_ROOT"' EXIT

for d in BUILD RPMS SOURCES SPECS SRPMS; do
    mkdir -p "$RPMBUILD_ROOT/$d"
done

STAGED_BIN="$RPMBUILD_ROOT/BUILD/beep"
cp "$BINARY" "$STAGED_BIN"
chmod 0755 "$STAGED_BIN"

cat > "$RPMBUILD_ROOT/SPECS/beep.spec" << EOF
Name:       beep
Version:    ${VERSION}
Release:    1%{?dist}
Summary:    Terminal-native AI coding assistant
License:    MIT
URL:        https://github.com/The-Tech-Idea/Beep.AI.Code
BuildArch:  ${RPM_ARCH}

%description
Beep.AI.Code is a CLI code assistant powered by Beep.AI.Server.
Supports interactive chat, one-shot prompts, an autonomous agent loop,
MCP tool integration, and portable agent bundles.

%install
install -d %{buildroot}/usr/local/bin
install -m 0755 %{_builddir}/beep %{buildroot}/usr/local/bin/beep

%files
/usr/local/bin/beep

%changelog
* $(date '+%a %b %d %Y') Beep.AI Team <support@beep.ai> - ${VERSION}-1
- Release ${VERSION}
EOF

rpmbuild -bb \
    --define "_topdir $RPMBUILD_ROOT" \
    "$RPMBUILD_ROOT/SPECS/beep.spec"

mkdir -p dist
BUILT_RPM="$(find "$RPMBUILD_ROOT/RPMS" -name "*.rpm" | head -1)"
OUTPUT="dist/beep-${VERSION}.${RPM_ARCH}.rpm"
cp "$BUILT_RPM" "$OUTPUT"
echo "Built: $OUTPUT"
