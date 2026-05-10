"""Clipboard integration."""

from __future__ import annotations

import subprocess


def get_clipboard() -> str | None:
    """Get clipboard content."""
    try:
        import platform
        system = platform.system()

        if system == "Windows":
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() or None

        if system == "Darwin":
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() or None

        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def set_clipboard(text: str) -> bool:
    """Set clipboard content."""
    try:
        import platform
        system = platform.system()

        if system == "Windows":
            subprocess.run(
                ["powershell", "-command", f"Set-Clipboard -Value {text!r}"],
                timeout=5,
            )
            return True

        if system == "Darwin":
            proc = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE,
            )
            proc.communicate(text.encode(), timeout=5)
            return True

        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard"],
            stdin=subprocess.PIPE,
        )
        proc.communicate(text.encode(), timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
