"""Shared probe helpers for autonomous-agent backend providers."""

from __future__ import annotations

from typing import Any

from beep.agent.provider_contracts import ProviderProbeResult


def _extract_model_ids(models: list[dict[str, Any]] | Any) -> list[str]:
    resolved: list[str] = []
    if not isinstance(models, list):
        return resolved
    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = model.get("id")
        if model_id is None:
            continue
        normalized = str(model_id).strip()
        if normalized and normalized not in resolved:
            resolved.append(normalized)
    return resolved


def _build_model_probe_result(
    models: list[dict[str, Any]] | Any,
    *,
    selected_model: str | None,
) -> ProviderProbeResult:
    model_ids = _extract_model_ids(models)
    if selected_model and model_ids:
        if selected_model in model_ids:
            return ProviderProbeResult(
                supported=True,
                success=True,
                message=f"Connected to /v1/models. Found {len(model_ids)} models including '{selected_model}'.",
            )
        preview = ", ".join(model_ids[:5])
        suffix = f" Available models: {preview}" if preview else ""
        return ProviderProbeResult(
            supported=True,
            success=False,
            message=f"Connected to /v1/models, but model '{selected_model}' was not returned.{suffix}",
        )
    if model_ids:
        return ProviderProbeResult(
            supported=True,
            success=True,
            message=f"Connected to /v1/models. Found {len(model_ids)} models.",
        )
    if selected_model:
        return ProviderProbeResult(
            supported=True,
            success=True,
            message=f"Connected to /v1/models, but the provider returned no models so '{selected_model}' could not be verified.",
        )
    return ProviderProbeResult(
        supported=True,
        success=True,
        message="Connected to /v1/models, but the provider returned no models.",
    )
