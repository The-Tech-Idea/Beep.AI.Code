"""Channel-specific local packaging plans for portable agent bundles."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Iterable

from beep import __version__ as CLI_VERSION
from beep.agent.bundle_contract import PortableAgentBundleManifest
from beep.agent.bundle_store import bundle_file_name
from beep.publishing.release_metadata import (
    build_distribution_name,
    build_shared_release_metadata,
    render_channel_release_metadata_json,
)
from beep.publishing.release_container_support import (
    build_container_files,
    build_github_release_files,
)

SUPPORTED_PACKAGE_CHANNELS: tuple[str, ...] = ("npm", "python", "github-release", "container")
_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9]+")


@dataclass(frozen=True)
class ChannelPackageFile:
    relative_path: str
    content: str


@dataclass(frozen=True)
class ChannelPackagePlan:
    channel: str
    root_dir_name: str
    package_name: str
    package_version: str
    metadata: dict[str, object]
    files: tuple[ChannelPackageFile, ...]


def _slugify(value: str, *, separator: str) -> str:
    normalized = _SLUG_PATTERN.sub(separator, str(value).strip().lower()).strip(separator)
    return normalized or "agent"


def _package_base_name(manifest: PortableAgentBundleManifest) -> str:
    return build_distribution_name(manifest.agent_id)


def _python_module_name(manifest: PortableAgentBundleManifest) -> str:
    return _slugify(f"beep_agent_{manifest.agent_id}", separator="_")


def _package_description(manifest: PortableAgentBundleManifest) -> str:
    return manifest.description.strip() or manifest.name.strip()


def _author_name(manifest: PortableAgentBundleManifest) -> str:
    return (
        manifest.provenance.publisher.strip()
        or manifest.provenance.created_by.strip()
        or "Beep.AI Team"
    )


def _unique_keywords(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value).strip().lower()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def build_channel_package_plans(
    manifest: PortableAgentBundleManifest,
    *,
    channels: Iterable[str] | None = None,
) -> tuple[ChannelPackagePlan, ...]:
    normalized_channels = _normalize_channels(channels)
    plans = tuple(build_channel_package_plan(manifest, channel=channel) for channel in normalized_channels)
    _validate_shared_plan_metadata(plans, manifest)
    return plans


def build_channel_package_plan(
    manifest: PortableAgentBundleManifest,
    *,
    channel: str,
) -> ChannelPackagePlan:
    normalized_channel = str(channel).strip().lower()
    if normalized_channel == "npm":
        return _build_npm_package_plan(manifest)
    if normalized_channel == "python":
        return _build_python_package_plan(manifest)
    if normalized_channel == "github-release":
        return _build_github_release_package_plan(manifest)
    if normalized_channel == "container":
        return _build_container_package_plan(manifest)
    raise ValueError(
        f"Unsupported package channel {channel!r}. Supported channels: {', '.join(SUPPORTED_PACKAGE_CHANNELS)}"
    )


def write_channel_package_plan(
    plan: ChannelPackagePlan,
    output_root: Path,
    *,
    overwrite: bool = False,
) -> Path:
    channel_root = output_root / plan.root_dir_name
    if channel_root.exists() and any(channel_root.iterdir()) and not overwrite:
        raise ValueError(f"Refusing to overwrite existing package directory: {channel_root}")
    channel_root.mkdir(parents=True, exist_ok=True)
    for package_file in plan.files:
        target_path = channel_root / Path(package_file.relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(package_file.content, encoding="utf-8")
    return channel_root


def _normalize_channels(channels: Iterable[str] | None) -> tuple[str, ...]:
    requested = list(channels or [])
    if not requested:
        return SUPPORTED_PACKAGE_CHANNELS
    normalized: list[str] = []
    for channel in requested:
        text = str(channel).strip().lower()
        if not text:
            continue
        if text not in SUPPORTED_PACKAGE_CHANNELS:
            raise ValueError(
                f"Unsupported package channel {channel!r}. Supported channels: {', '.join(SUPPORTED_PACKAGE_CHANNELS)}"
            )
        if text not in normalized:
            normalized.append(text)
    if not normalized:
        return SUPPORTED_PACKAGE_CHANNELS
    return tuple(normalized)


def _validate_shared_plan_metadata(
    plans: tuple[ChannelPackagePlan, ...],
    manifest: PortableAgentBundleManifest,
) -> None:
    expected_version = manifest.bundle_version
    expected_agent_id = manifest.agent_id
    expected_description = _package_description(manifest)
    expected_bundle_file = bundle_file_name(manifest.agent_id)
    for plan in plans:
        if plan.package_version != expected_version:
            raise ValueError(f"Package plan {plan.channel!r} does not match bundle version {expected_version}")
        if plan.metadata.get("agent_id") != expected_agent_id:
            raise ValueError(f"Package plan {plan.channel!r} does not preserve the bundle agent_id")
        if plan.metadata.get("description") != expected_description:
            raise ValueError(f"Package plan {plan.channel!r} does not preserve the bundle description")
        if plan.metadata.get("bundle_file") != expected_bundle_file:
            raise ValueError(f"Package plan {plan.channel!r} does not preserve the bundle filename")
        shared_release_metadata = plan.metadata.get("shared_release_metadata")
        if not isinstance(shared_release_metadata, dict):
            raise ValueError(f"Package plan {plan.channel!r} does not expose shared release metadata")
        if shared_release_metadata.get("agent_id") != expected_agent_id:
            raise ValueError(f"Package plan {plan.channel!r} does not preserve shared release agent_id")
        if shared_release_metadata.get("description") != expected_description:
            raise ValueError(f"Package plan {plan.channel!r} does not preserve shared release description")
        if shared_release_metadata.get("bundle_file") != expected_bundle_file:
            raise ValueError(f"Package plan {plan.channel!r} does not preserve shared release bundle filename")
        if shared_release_metadata.get("bundle_version") != expected_version:
            raise ValueError(f"Package plan {plan.channel!r} does not preserve shared release bundle version")
        if not any(package_file.relative_path == "release-metadata.json" for package_file in plan.files):
            raise ValueError(f"Package plan {plan.channel!r} does not include a release-metadata.json artifact")
        if not any(package_file.relative_path.endswith(expected_bundle_file) for package_file in plan.files):
            raise ValueError(f"Package plan {plan.channel!r} does not include the portable bundle payload")


def _build_plan_metadata(
    manifest: PortableAgentBundleManifest,
    *,
    package_name: str,
    bundle_name: str,
) -> dict[str, object]:
    shared_release_metadata = build_shared_release_metadata(
        manifest,
        distribution_name=package_name,
        bundle_file=bundle_name,
        description=_package_description(manifest),
    )
    return {
        "agent_id": manifest.agent_id,
        "description": _package_description(manifest),
        "bundle_file": bundle_name,
        "shared_release_metadata": shared_release_metadata.to_dict(),
    }


def _build_npm_package_plan(manifest: PortableAgentBundleManifest) -> ChannelPackagePlan:
    package_name = _package_base_name(manifest)
    bundle_name = bundle_file_name(manifest.agent_id)
    bundle_relative_path = f"bundle/{bundle_name}"
    shared_release_metadata = build_shared_release_metadata(
        manifest,
        distribution_name=package_name,
        bundle_file=bundle_name,
        description=_package_description(manifest),
    )
    keywords = _unique_keywords([
        "beep-ai",
        "portable-agent",
        "agent-bundle",
        *manifest.tags,
    ])
    package_payload = {
        "name": package_name,
        "version": manifest.bundle_version,
        "description": _package_description(manifest),
        "type": "commonjs",
        "main": "index.cjs",
        "exports": {
            ".": {
                "default": "./index.cjs",
            }
        },
        "sideEffects": False,
        "files": ["README.md", "index.cjs", bundle_relative_path],
        "keywords": keywords,
        "author": _author_name(manifest),
        "license": "MIT",
        "dependencies": {
            "beep-ai-sdk": "^1.0.0",
        },
        "engines": {
            "node": ">=18.0.0",
        },
        "publishConfig": {
            "access": "public",
        },
        "beepAgentBundle": {
            "agentId": manifest.agent_id,
            "bundlePath": bundle_relative_path,
            "releaseMetadataPath": "release-metadata.json",
            "schemaVersion": manifest.schema_version,
        },
    }
    package_payload["files"].insert(1, "release-metadata.json")
    return ChannelPackagePlan(
        channel="npm",
        root_dir_name="npm",
        package_name=package_name,
        package_version=manifest.bundle_version,
        metadata=_build_plan_metadata(manifest, package_name=package_name, bundle_name=bundle_name),
        files=(
            ChannelPackageFile(
                relative_path="package.json",
                content=json.dumps(package_payload, indent=2, sort_keys=True) + "\n",
            ),
            ChannelPackageFile(
                relative_path="release-metadata.json",
                content=render_channel_release_metadata_json(
                    shared_release_metadata,
                    channel="npm",
                    output_kind="local-package",
                    channel_metadata={
                        "bundle_path": bundle_relative_path,
                        "main": "index.cjs",
                        "publish_access": "public",
                    },
                ),
            ),
            ChannelPackageFile(
                relative_path="index.cjs",
                content=_build_npm_entrypoint(bundle_relative_path),
            ),
            ChannelPackageFile(
                relative_path="README.md",
                content=_build_npm_readme(manifest, package_name, bundle_relative_path),
            ),
            ChannelPackageFile(
                relative_path=bundle_relative_path,
                content=manifest.to_json(),
            ),
        ),
    )


def _build_python_package_plan(manifest: PortableAgentBundleManifest) -> ChannelPackagePlan:
    package_name = _package_base_name(manifest)
    module_name = _python_module_name(manifest)
    bundle_name = bundle_file_name(manifest.agent_id)
    bundle_relative_path = f"src/{module_name}/resources/{bundle_name}"
    shared_release_metadata = build_shared_release_metadata(
        manifest,
        distribution_name=package_name,
        bundle_file=bundle_name,
        description=_package_description(manifest),
    )
    return ChannelPackagePlan(
        channel="python",
        root_dir_name="python",
        package_name=package_name,
        package_version=manifest.bundle_version,
        metadata=_build_plan_metadata(manifest, package_name=package_name, bundle_name=bundle_name),
        files=(
            ChannelPackageFile(
                relative_path="pyproject.toml",
                content=_build_python_pyproject(manifest, package_name, module_name),
            ),
            ChannelPackageFile(
                relative_path="release-metadata.json",
                content=render_channel_release_metadata_json(
                    shared_release_metadata,
                    channel="python",
                    output_kind="local-package",
                    channel_metadata={
                        "bundle_path": bundle_relative_path,
                        "module_name": module_name,
                        "requires_python": ">=3.11",
                    },
                ),
            ),
            ChannelPackageFile(
                relative_path="README.md",
                content=_build_python_readme(manifest, package_name, module_name),
            ),
            ChannelPackageFile(
                relative_path=f"src/{module_name}/__init__.py",
                content=_build_python_init(manifest, module_name, bundle_name),
            ),
            ChannelPackageFile(
                relative_path=bundle_relative_path,
                content=manifest.to_json(),
            ),
        ),
    )


def _build_github_release_package_plan(manifest: PortableAgentBundleManifest) -> ChannelPackagePlan:
    package_name = _package_base_name(manifest)
    bundle_name = bundle_file_name(manifest.agent_id)
    shared_release_metadata = build_shared_release_metadata(
        manifest,
        distribution_name=package_name,
        bundle_file=bundle_name,
        description=_package_description(manifest),
    )
    files = build_github_release_files(
        manifest,
        package_name=package_name,
        bundle_name=bundle_name,
        description=_package_description(manifest),
        shared_release_metadata=shared_release_metadata,
    )
    return ChannelPackagePlan(
        channel="github-release",
        root_dir_name="github-release",
        package_name=package_name,
        package_version=manifest.bundle_version,
        metadata=_build_plan_metadata(manifest, package_name=package_name, bundle_name=bundle_name),
        files=tuple(
            ChannelPackageFile(relative_path=relative_path, content=content)
            for relative_path, content in files
        ),
    )


def _build_container_package_plan(manifest: PortableAgentBundleManifest) -> ChannelPackagePlan:
    package_name = _package_base_name(manifest)
    bundle_name = bundle_file_name(manifest.agent_id)
    shared_release_metadata = build_shared_release_metadata(
        manifest,
        distribution_name=package_name,
        bundle_file=bundle_name,
        description=_package_description(manifest),
    )
    files = build_container_files(
        manifest,
        package_name=package_name,
        bundle_name=bundle_name,
        description=_package_description(manifest),
        shared_release_metadata=shared_release_metadata,
    )
    return ChannelPackagePlan(
        channel="container",
        root_dir_name="container",
        package_name=package_name,
        package_version=manifest.bundle_version,
        metadata=_build_plan_metadata(manifest, package_name=package_name, bundle_name=bundle_name),
        files=tuple(
            ChannelPackageFile(relative_path=relative_path, content=content)
            for relative_path, content in files
        ),
    )


def _build_npm_entrypoint(bundle_relative_path: str) -> str:
    return (
        '"use strict";\n\n'
        "const fs = require(\"node:fs\");\n"
        "const path = require(\"node:path\");\n\n"
        f"const bundlePath = path.join(__dirname, ...{json.dumps(bundle_relative_path.split('/'))});\n"
        "let cachedManifest = null;\n\n"
        "function loadBundle() {\n"
        "  if (cachedManifest !== null) {\n"
        "    return cachedManifest;\n"
        "  }\n"
        "  cachedManifest = JSON.parse(fs.readFileSync(bundlePath, \"utf8\"));\n"
        "  return cachedManifest;\n"
        "}\n\n"
        "module.exports = {\n"
        "  bundlePath,\n"
        "  loadBundle,\n"
        "  manifest: loadBundle(),\n"
        "};\n"
    )


def _build_npm_readme(
    manifest: PortableAgentBundleManifest,
    package_name: str,
    bundle_relative_path: str,
) -> str:
    description = _package_description(manifest)
    return (
        f"# {package_name}\n\n"
        f"{description}\n\n"
        "This package is a local wrapper around a Phase 17 portable Beep.AI agent bundle. "
        "It exposes the bundled manifest for inspection and later publish/deployment adapters. "
        "The shared release metadata is written to `release-metadata.json`.\n\n"
        "## Included Files\n\n"
        f"- `{bundle_relative_path}`\n"
        "- `release-metadata.json`\n"
        "- `index.cjs`\n\n"
        "## Usage\n\n"
        "```javascript\n"
        f"const agentBundle = require(\"{package_name}\");\n\n"
        "const manifest = agentBundle.loadBundle();\n"
        "console.log(manifest.agent_id, manifest.bundle_version);\n"
        "```\n"
    )


def _build_python_pyproject(
    manifest: PortableAgentBundleManifest,
    package_name: str,
    module_name: str,
) -> str:
    description = _package_description(manifest).replace('"', "'")
    author_name = _author_name(manifest).replace('"', "'")
    return (
        "[build-system]\n"
        "requires = [\"hatchling\"]\n"
        "build-backend = \"hatchling.build\"\n\n"
        "[project]\n"
        f'name = "{package_name}"\n'
        f'version = "{manifest.bundle_version}"\n'
        f'description = "{description}"\n'
        'readme = "README.md"\n'
        'license = {text = "MIT"}\n'
        'requires-python = ">=3.11"\n'
        f'authors = [{{name = "{author_name}"}}]\n'
        'dependencies = [\n'
        f'    "beep-ai-code>={CLI_VERSION}",\n'
        ']\n\n'
        '[tool.hatch.build]\n'
        'include = [\n'
        '    "README.md",\n'
        '    "release-metadata.json",\n'
        f'    "src/{module_name}/**/*.py",\n'
        f'    "src/{module_name}/resources/*.json",\n'
        ']\n\n'
        '[tool.hatch.build.targets.wheel]\n'
        f'packages = ["src/{module_name}"]\n'
    )


def _build_python_init(
    manifest: PortableAgentBundleManifest,
    module_name: str,
    bundle_name: str,
) -> str:
    del module_name
    return (
        '"""Local Python wrapper for a portable Beep.AI agent bundle."""\n\n'
        'from __future__ import annotations\n\n'
        'from contextlib import contextmanager\n'
        'import json\n'
        'from importlib.resources import as_file, files\n'
        'from pathlib import Path\n'
        'from typing import Any, Iterator\n\n'
        f'__version__ = "{manifest.bundle_version}"\n\n'
        f'_BUNDLE_RESOURCE = files(__package__).joinpath("resources/{bundle_name}")\n\n'
        '@contextmanager\n'
        'def bundle_path() -> Iterator[Path]:\n'
        '    with as_file(_BUNDLE_RESOURCE) as resolved_path:\n'
        '        yield resolved_path\n\n'
        'def load_manifest() -> dict[str, Any]:\n'
        '    return json.loads(_BUNDLE_RESOURCE.read_text(encoding="utf-8"))\n\n'
        '__all__ = ["__version__", "bundle_path", "load_manifest"]\n'
    )


def _build_python_readme(
    manifest: PortableAgentBundleManifest,
    package_name: str,
    module_name: str,
) -> str:
    description = _package_description(manifest)
    return (
        f"# {package_name}\n\n"
        f"{description}\n\n"
        "This package is a local Python wrapper around a Phase 17 portable Beep.AI agent bundle. "
        "It keeps the bundle payload available to build and publish tooling without redefining agent semantics. "
        "The shared release metadata is written to `release-metadata.json`.\n\n"
        "## Usage\n\n"
        "```python\n"
        f"from {module_name} import bundle_path, load_manifest\n\n"
        "manifest = load_manifest()\n"
        "print(manifest[\"agent_id\"], manifest[\"bundle_version\"])\n\n"
        "with bundle_path() as path:\n"
        "    print(path)\n"
        "```\n"
    )