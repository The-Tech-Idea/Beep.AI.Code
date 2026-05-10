"""Helpers for building public agent CLI input payloads."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from beep.agent.graph_runner import InitialUserContent
from beep.workspace.binary_detector import is_binary_file

_IMAGE_SUFFIX_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_MAX_INLINE_TEXT_FILE_CHARS = 20_000
_MAX_INLINE_IMAGE_BYTES = 5 * 1024 * 1024


def build_agent_response_format(
    *,
    response_json: bool,
    response_schema: Path | None,
) -> dict[str, Any] | None:
    """Build a public response_format payload from CLI flags."""
    if response_json and response_schema is not None:
        raise ValueError("Choose either --response-json or --response-schema, not both.")
    if response_json:
        return {"type": "json_object"}
    if response_schema is None:
        return None

    schema_payload = _read_json_file(response_schema)
    if not isinstance(schema_payload, dict):
        raise ValueError(f"Response schema file must contain a JSON object: {response_schema}")
    if _looks_like_response_format(schema_payload):
        return schema_payload
    return {
        "type": "json_schema",
        "json_schema": {
            "name": _normalize_schema_name(response_schema.stem),
            "schema": schema_payload,
        },
    }


def build_agent_initial_user_content(
    *,
    input_files: list[Path] | None,
    input_images: list[Path] | None,
) -> InitialUserContent | None:
    """Build multimodal initial user content from CLI file and image flags."""
    content_blocks: list[dict[str, Any]] = []
    for path in input_files or []:
        content_blocks.append(_text_file_block(path))
    for path in input_images or []:
        content_blocks.extend(_image_blocks(path))
    return content_blocks or None


def _read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to read JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _normalize_schema_name(name: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in name).strip("_")
    return cleaned or "agent_response"


def _looks_like_response_format(payload: dict[str, Any]) -> bool:
    format_type = str(payload.get("type") or "").strip().lower()
    return format_type in {"json_object", "json_schema", "text"}


def _ensure_readable_file(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"Input path does not exist: {path}")
    if not resolved.is_file():
        raise ValueError(f"Input path must be a file: {path}")
    return resolved


def _text_file_block(path: Path) -> dict[str, Any]:
    resolved = _ensure_readable_file(path)
    if is_binary_file(resolved):
        raise ValueError(
            f"Input file appears to be binary. Use --input-image for supported images instead: {resolved}"
        )
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ValueError(f"Unable to read input file {resolved}: {exc}") from exc
    if len(content) > _MAX_INLINE_TEXT_FILE_CHARS:
        content = (
            content[:_MAX_INLINE_TEXT_FILE_CHARS].rstrip()
            + f"\n\n[truncated to {_MAX_INLINE_TEXT_FILE_CHARS} characters]"
        )
    return {
        "type": "text",
        "text": f"Attached file: {resolved.name}\nPath: {resolved}\n\n{content}",
    }


def _image_blocks(path: Path) -> list[dict[str, Any]]:
    resolved = _ensure_readable_file(path)
    mime = _IMAGE_SUFFIX_TO_MIME.get(resolved.suffix.lower())
    if mime is None:
        supported = ", ".join(sorted(_IMAGE_SUFFIX_TO_MIME))
        raise ValueError(
            f"Unsupported image type for {resolved}. Supported suffixes: {supported}"
        )
    try:
        image_bytes = resolved.read_bytes()
    except OSError as exc:
        raise ValueError(f"Unable to read input image {resolved}: {exc}") from exc
    if len(image_bytes) > _MAX_INLINE_IMAGE_BYTES:
        raise ValueError(
            f"Input image is too large ({len(image_bytes)} bytes). Limit is {_MAX_INLINE_IMAGE_BYTES} bytes."
        )
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return [
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
        {"type": "text", "text": f"Attached image: {resolved.name}"},
    ]