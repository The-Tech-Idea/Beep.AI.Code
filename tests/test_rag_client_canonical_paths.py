"""Ensure production Beep.AI.Code modules use canonical /v1/rag/* paths."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BEEP = _ROOT / "beep"

# Compat constants may remain in endpoints.py only until server sunset.
_ALLOWED_COMPAT_FILE = _ROOT / "beep" / "api" / "endpoints.py"


def test_beep_code_production_modules_do_not_call_v1_api_rag_paths():
    offenders: list[str] = []
    for path in _BEEP.rglob("*.py"):
        if path == _ALLOWED_COMPAT_FILE:
            continue
        text = path.read_text(encoding="utf-8")
        if "/v1/api/rag" in text:
            offenders.append(str(path.relative_to(_ROOT)))
    assert not offenders, f"Use /v1/rag/* instead of compat paths in: {offenders}"
