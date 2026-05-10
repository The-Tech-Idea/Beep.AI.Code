"""Module entry point for structured error handling."""

from __future__ import annotations

from beep.errors.classifier import classify_error
from beep.errors.injector import format_error_injection, inject_errors_into_messages
from beep.errors.models import ErrorCategory, ErrorHistory, StructuredToolError

__all__ = [
    "ErrorCategory",
    "ErrorHistory",
    "StructuredToolError",
    "classify_error",
    "format_error_injection",
    "inject_errors_into_messages",
]
