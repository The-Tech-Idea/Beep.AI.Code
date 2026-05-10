"""Support builders for GitHub release and container package channels."""

from __future__ import annotations

import json

from beep import __version__ as CLI_VERSION
from beep.agent.bundle_contract import PortableAgentBundleManifest
from beep.publishing.release_metadata import (
    SharedReleaseMetadata,
    render_channel_release_metadata_json,
)


def build_github_release_files(
    manifest: PortableAgentBundleManifest,
    *,
    package_name: str,
    bundle_name: str,
    description: str,
    shared_release_metadata: SharedReleaseMetadata,
) -> tuple[tuple[str, str], ...]:
    bundle_relative_path = f"assets/{bundle_name}"
    checksum_relative_path = "assets/SHA256SUMS"
    release_payload = {
        "draft": True,
        "prerelease": True,
        "asset_files": ["release-metadata.json", bundle_relative_path, checksum_relative_path],
    }
    release_notes = (
        f"# {manifest.name} {manifest.bundle_version}\n\n"
        f"{description}\n\n"
        "## Included Assets\n\n"
        "- `release-metadata.json`\n"
        f"- `{bundle_relative_path}`\n"
        f"- `{checksum_relative_path}`\n\n"
        "## Publish Notes\n\n"
        "This directory is a dry-run GitHub release asset layout for a portable Beep.AI agent bundle. "
        "Shared provenance and compatibility metadata is recorded in `release-metadata.json`.\n"
    )
    checksum_content = f"TO-BE-GENERATED  {bundle_name}\n"
    return (
        (
            "release-metadata.json",
            render_channel_release_metadata_json(
                shared_release_metadata,
                channel="github-release",
                output_kind="local-package",
                channel_metadata=release_payload,
            ),
        ),
        ("RELEASE_NOTES.md", release_notes),
        (bundle_relative_path, manifest.to_json()),
        (checksum_relative_path, checksum_content),
    )


def build_container_files(
    manifest: PortableAgentBundleManifest,
    *,
    package_name: str,
    bundle_name: str,
    description: str,
    shared_release_metadata: SharedReleaseMetadata,
) -> tuple[tuple[str, str], ...]:
    bundle_relative_path = f"bundle/{bundle_name}"
    dockerfile = (
        "FROM python:3.11-slim\n\n"
        f'LABEL org.opencontainers.image.title="{manifest.name}" \\\n'
        f'      org.opencontainers.image.version="{manifest.bundle_version}" \\\n'
        f'      org.opencontainers.image.description="{description}"\n\n'
        "ENV BEEP_AGENT_BUNDLE=/opt/beep-agent/"
        f"{bundle_relative_path}\n"
        "WORKDIR /opt/beep-agent\n"
        f"COPY {bundle_relative_path} /opt/beep-agent/{bundle_relative_path}\n"
        "COPY entrypoint.sh /opt/beep-agent/entrypoint.sh\n"
        f'RUN pip install --no-cache-dir "beep-ai-code>={CLI_VERSION}"\n'
        "ENTRYPOINT [\"/opt/beep-agent/entrypoint.sh\"]\n"
    )
    dockerignore = (
        "**\n"
        "!Dockerfile\n"
        "!README.md\n"
        "!release-metadata.json\n"
        "!entrypoint.sh\n"
        "!bundle/\n"
        f"!{bundle_relative_path}\n"
    )
    entrypoint = (
        "#!/bin/sh\n"
        "set -eu\n\n"
        "if [ \"$#\" -eq 0 ]; then\n"
        "  echo \"Usage: docker run --rm <image> <goal>\" >&2\n"
        "  exit 2\n"
        "fi\n\n"
        "exec python -m beep agent run \"$BEEP_AGENT_BUNDLE\" \"$@\"\n"
    )
    readme = (
        f"# {package_name} container\n\n"
        f"{description}\n\n"
        "This directory is a dry-run container wrapper for a portable Beep.AI agent bundle. "
        "It installs the CLI runtime, copies the canonical bundle, and forwards container arguments to `beep agent run`. "
        "Shared provenance and compatibility metadata is recorded in `release-metadata.json`.\n\n"
        "## Usage\n\n"
        "```bash\n"
        f"docker build -t {package_name}:{manifest.bundle_version} .\n"
        f"docker run --rm {package_name}:{manifest.bundle_version} inspect this repo\n"
        "```\n"
    )
    return (
        ("Dockerfile", dockerfile),
        (".dockerignore", dockerignore),
        ("entrypoint.sh", entrypoint),
        (
            "release-metadata.json",
            render_channel_release_metadata_json(
                shared_release_metadata,
                channel="container",
                output_kind="local-package",
                channel_metadata={
                    "base_image": "python:3.11-slim",
                    "bundle_path": bundle_relative_path,
                    "entrypoint_path": "entrypoint.sh",
                    "image_reference": f"{package_name}:{manifest.bundle_version}",
                },
            ),
        ),
        ("README.md", readme),
        (bundle_relative_path, manifest.to_json()),
    )