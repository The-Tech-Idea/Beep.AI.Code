"""Startup flow — profile-first initialization.

Replaces the old "check config → run wizard" flow with:
1. Check for saved profile → skip directly to UI
2. No profile? → Run Simple Service Generator flow (hardware + profile picker + wizard)
3. No server? → Fall back to local config wizard

This module bridges the old ``ensure_configured`` pattern with the new
profile-driven onboarding.
"""

from __future__ import annotations

import logging
from typing import Any

from beep.config import BeepConfig, load_config, save_config
from beep.profiles import (
    UserProfile,
    has_saved_profile,
    load_active_profile,
    save_active_profile,
)

logger = logging.getLogger(__name__)


def profile_aware_startup(
    server_url: str = "http://localhost:5000",
    api_token: str | None = None,
) -> StartupResult:
    """Run the profile-aware startup flow.

    Returns a StartupResult describing what happened and what to do next.
    """
    # 1. Check for saved profile
    if has_saved_profile():
        profile = load_active_profile()
        if profile is not None:
            return StartupResult(
                status="profile_loaded",
                profile=profile,
                message=f"Welcome back, {profile.profile_display_name}",
            )

    # 2. Check if basic config exists (for existing CLI users)
    config = load_config()
    if config.is_configured and config.has_profile:
        return StartupResult(
            status="config_exists",
            profile=None,
            message="Configuration found. Run 'beep setup-profile' to set up a profile.",
        )

    # 3. No profile, no config — need setup
    return StartupResult(
        status="needs_setup",
        profile=None,
        message="Welcome to Beep.AI! Let's get you set up.",
    )


class StartupResult:
    """Result of the profile-aware startup check."""

    def __init__(
        self,
        status: str,
        profile: UserProfile | None = None,
        message: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.status = status           # "profile_loaded" | "config_exists" | "needs_setup"
        self.profile = profile
        self.message = message
        self.extra = extra or {}


def apply_profile_to_config(profile: UserProfile) -> BeepConfig:
    """Apply profile settings to the BeepConfig and save."""
    config = load_config()

    # Apply profile fields
    config.profile_id = profile.profile_id
    config.profile_display_name = profile.profile_display_name
    config.profile_icon = profile.profile_icon

    # Apply connection if profile has it
    if profile.server_url:
        config.server_url = profile.server_url
    if profile.api_token:
        config.api_token = profile.api_token

    # Apply model preference
    if profile.model and profile.model.model_id:
        config.default_model = profile.model.model_id

    save_config(config)
    return config


def build_profile_from_setup_answers(
    profile_id: str,
    display_name: str,
    icon: str,
    server_url: str,
    api_token: str | None,
    answers: dict[str, Any],
    created_services: list[str],
    model_id: str | None = None,
) -> UserProfile:
    """Build a UserProfile from wizard answers and created services."""
    from beep.profiles import HardwareInfo, ModelChoice

    profile = UserProfile(
        profile_id=profile_id,
        profile_display_name=display_name,
        profile_icon=icon,
        server_url=server_url,
        api_token=api_token,
        hardware=HardwareInfo(),
        model=ModelChoice(
            model_id=model_id or "auto-detected",
            label="",
            is_custom=model_id is not None,
        ),
        wizard_answers=answers,
        created_services=created_services,
    )
    save_active_profile(profile)
    return profile
