"""Bridge to Beep.AI.Server Simple Service Generator API.

Calls /v1/api/simple/* endpoints (token-auth required) to run the
profile-driven setup flow from the CLI, then saves the result as a local profile.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from beep.profiles import (
    HardwareInfo,
    ModelChoice,
    UserProfile,
    save_active_profile,
)

logger = logging.getLogger(__name__)


async def detect_hardware_from_server(server_url: str) -> HardwareInfo | None:
    """Call the server to get hardware info. Returns None if unreachable."""
    try:
        async with httpx.AsyncClient(base_url=server_url.rstrip("/"), timeout=10.0) as client:
            resp = await client.get("/v1/api/simple/profiles")
            if resp.status_code != 200:
                return None
            data = resp.json()
            # The profiles endpoint includes hardware tier info
            tier = data.get("hardware_tier", "good")
            label = data.get("hardware_label", "")
            return HardwareInfo(
                gpu_name=None,
                vram_gb=0.0,
                ram_gb=8.0 if tier == "basic" else 16.0,
                disk_free_gb=10.0,
                can_run_gpu_models=(tier == "great"),
            )
    except Exception as e:
        logger.debug(f"Hardware detection failed: {e}")
        return None


async def list_available_profiles(server_url: str) -> dict[str, Any]:
    """Get profiles the user's hardware can run."""
    async with httpx.AsyncClient(base_url=server_url.rstrip("/"), timeout=10.0) as client:
        resp = await client.get("/v1/api/simple/profiles")
        resp.raise_for_status()
        return resp.json()


async def preview_batch(
    server_url: str,
    profile_id: str,
    answers: dict[str, Any],
) -> dict[str, Any]:
    """Preview what will be created WITHOUT actually creating."""
    async with httpx.AsyncClient(base_url=server_url.rstrip("/"), timeout=10.0) as client:
        resp = await client.post(
            "/v1/api/simple/batch/preview",
            json={"profile_id": profile_id, "answers": answers},
        )
        resp.raise_for_status()
        return resp.json()


async def create_batch_and_save_profile(
    server_url: str,
    profile_id: str,
    profile_display_name: str,
    profile_icon: str,
    answers: dict[str, Any],
    api_token: str | None = None,
    custom_model: str | None = None,
) -> tuple[str, UserProfile]:
    """Create the batch on the server AND save the profile locally.

    Returns (batch_id, saved_profile).
    """
    headers = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    # Include custom model in answers if provided
    request_answers = dict(answers)
    if custom_model:
        request_answers["_custom_model"] = custom_model

    async with httpx.AsyncClient(
        base_url=server_url.rstrip("/"),
        headers=headers,
        timeout=30.0,
    ) as client:
        # Get hardware info
        hw_resp = await client.get("/v1/api/simple/profiles")
        hw_data = hw_resp.json() if hw_resp.status_code == 200 else {}

        # Create batch
        resp = await client.post(
            "/v1/api/simple/batch/create",
            json={"profile_id": profile_id, "answers": request_answers},
        )
        resp.raise_for_status()
        data = resp.json()
        batch_id = data["batch_id"]

        # Build and save profile
        profile = UserProfile(
            profile_id=profile_id,
            profile_display_name=profile_display_name,
            profile_icon=profile_icon,
            server_url=server_url,
            api_token=api_token,
            hardware=HardwareInfo(
                vram_gb=0.0,
                ram_gb=8.0,
                disk_free_gb=10.0,
            ),
            model=ModelChoice(
                model_id=custom_model or "auto-detected",
                label="",
                is_custom=custom_model is not None,
                hardware_tier=hw_data.get("hardware_tier", "good"),
            ),
            wizard_answers=answers,
            created_services=data.get("service_names", []),
        )
        save_active_profile(profile)

        return batch_id, profile


async def poll_batch_progress(
    server_url: str,
    batch_id: str,
    api_token: str | None = None,
) -> dict[str, Any]:
    """Poll for batch creation progress."""
    headers = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    async with httpx.AsyncClient(
        base_url=server_url.rstrip("/"),
        headers=headers,
        timeout=10.0,
    ) as client:
        resp = await client.get(f"/v1/api/simple/batch/{batch_id}/progress")
        resp.raise_for_status()
        return resp.json()
