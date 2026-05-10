"""Local Python wrapper for a portable Beep.AI agent bundle."""

from __future__ import annotations

from contextlib import contextmanager
import json
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any, Iterator

__version__ = "1.0.0"

_BUNDLE_RESOURCE = files(__package__).joinpath("resources/code-reviewer.beep-agent.json")

@contextmanager
def bundle_path() -> Iterator[Path]:
    with as_file(_BUNDLE_RESOURCE) as resolved_path:
        yield resolved_path

def load_manifest() -> dict[str, Any]:
    return json.loads(_BUNDLE_RESOURCE.read_text(encoding="utf-8"))

__all__ = ["__version__", "bundle_path", "load_manifest"]
