"""Shared typed capability primitives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityFlag:
    """Typed existence flag for one capability."""

    exists: bool
    notes: str = ""