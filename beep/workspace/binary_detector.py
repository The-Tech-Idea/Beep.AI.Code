"""Binary file detection."""

from __future__ import annotations

from pathlib import Path

_PROBE_BYTES = 8192


def is_binary_file(path: Path) -> bool:
    """Return True if the file appears to be binary.

    Detection: reads the first 8 KB and checks for null bytes.
    Non-existent or unreadable files are treated as binary to be safe.
    """
    try:
        chunk = path.read_bytes()[:_PROBE_BYTES]
    except OSError:
        return True
    return b"\x00" in chunk
