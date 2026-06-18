"""Profile configuration — persisted user profile state.

Stores the user's chosen profile, hardware info, model selection,
and connection details so the app can skip the wizard on restart.

Location: ``~/.beepai/profiles/active.json``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


PROFILES_DIR = Path.home() / ".beepai" / "profiles"
ACTIVE_PROFILE_FILE = PROFILES_DIR / "active.json"
PROFILE_SCHEMA_VERSION = 1


class HardwareInfo(BaseModel):
    """Detected hardware capabilities saved at profile creation time."""

    gpu_name: str | None = None
    vram_gb: float = 0.0
    ram_gb: float = 0.0
    disk_free_gb: float = 0.0
    gpu_type: str = "none"
    can_run_gpu_models: bool = False
    apple_silicon_chip: str | None = None
    mlx_available: bool = False


class ModelChoice(BaseModel):
    """The AI model the user selected (or auto-picked)."""

    model_id: str
    label: str = ""                       # "high-quality", "very good", "good", etc.
    download_size_gb: float = 0.0
    is_custom: bool = False               # True if user overrode the recommendation
    hardware_tier: str = "good"           # GREAT, GOOD, BASIC, MINIMAL


class UserProfile(BaseModel):
    """Persisted user profile — loaded on app startup to skip wizard."""

    schema_version: int = Field(default=PROFILE_SCHEMA_VERSION)
    profile_id: str                       # "team_lead_dev", "business_analyst", etc.
    profile_display_name: str             # "Team Lead (Development)"
    profile_icon: str = ""                # "👥"

    # Connection
    server_url: str = "http://localhost:5000"
    api_token: str | None = None

    # Hardware (detected at creation time)
    hardware: HardwareInfo = Field(default_factory=HardwareInfo)

    # Model
    model: ModelChoice = Field(
        default_factory=lambda: ModelChoice(model_id="phi-3-mini-4k", label="good")
    )

    # Answers from the wizard (maps to Simple Service Generator answers)
    wizard_answers: dict[str, Any] = Field(default_factory=dict)

    # Services the wizard created
    created_services: list[str] = Field(default_factory=list)

    # Theme
    theme: str = "dark"                   # "dark", "light", "high-contrast"
    theme_accent: str = "#58a6ff"         # Profile-specific accent color

    @property
    def is_developer(self) -> bool:
        """Developer profile gets full admin UI."""
        return self.profile_id == "developer"

    @property
    def landing_route(self) -> str:
        """Where the user lands after profile loads."""
        routes: dict[str, str] = {
            "team_lead_dev": "/dev/chat/",
            "business_analyst": "/search/",
            "team_lead_biz": "/biz/chat/",
            "content_creator": "/create/",
            "student": "/chat/",
            "solo_founder": "/build/",
            "developer": "/admin/",
            "it_admin": "/admin/",
        }
        return routes.get(self.profile_id, "/chat/")

    @property
    def theme_tokens(self) -> dict[str, str]:
        """CSS theme tokens based on profile."""
        themes: dict[str, dict[str, str]] = {
            "team_lead_dev": {
                "--app-bg": "#0d1117",
                "--sidebar-bg": "#161b22",
                "--accent": "#58a6ff",
                "--chat-user-bg": "#1a2332",
                "--chat-assistant-bg": "#0d1117",
                "--code-bg": "#0d1117",
                "--border": "#30363d",
            },
            "business_analyst": {
                "--app-bg": "#ffffff",
                "--sidebar-bg": "#f6f8fa",
                "--accent": "#0969da",
                "--chat-user-bg": "#e8f0fe",
                "--chat-assistant-bg": "#ffffff",
                "--code-bg": "#f6f8fa",
                "--border": "#d0d7de",
            },
            "team_lead_biz": {
                "--app-bg": "#1b1b2f",
                "--sidebar-bg": "#162447",
                "--accent": "#1f6f8b",
                "--chat-user-bg": "#1f4068",
                "--chat-assistant-bg": "#1b1b2f",
                "--code-bg": "#162447",
                "--border": "#1f6f8b",
            },
            "content_creator": {
                "--app-bg": "#1a1a2e",
                "--sidebar-bg": "#16213e",
                "--accent": "#e94560",
                "--chat-user-bg": "#0f3460",
                "--chat-assistant-bg": "#1a1a2e",
                "--code-bg": "#16213e",
                "--border": "#533483",
            },
            "student": {
                "--app-bg": "#fafafa",
                "--sidebar-bg": "#f0f0f0",
                "--accent": "#2ea043",
                "--chat-user-bg": "#e6f4ea",
                "--chat-assistant-bg": "#fafafa",
                "--code-bg": "#f6f8fa",
                "--border": "#d0d7de",
            },
            "solo_founder": {
                "--app-bg": "#0f0e17",
                "--sidebar-bg": "#1a1932",
                "--accent": "#ff8906",
                "--chat-user-bg": "#2d1b69",
                "--chat-assistant-bg": "#0f0e17",
                "--code-bg": "#1a1932",
                "--border": "#ff8906",
            },
        }
        return themes.get(self.profile_id, themes["team_lead_dev"])


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_active_profile(profile: UserProfile) -> None:
    """Persist the active profile to disk."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump()
    import json
    ACTIVE_PROFILE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_active_profile() -> UserProfile | None:
    """Load the persisted profile, or None if not found."""
    if not ACTIVE_PROFILE_FILE.exists():
        return None
    try:
        import json
        data = json.loads(ACTIVE_PROFILE_FILE.read_text(encoding="utf-8"))
        return UserProfile(**data)
    except Exception:
        return None


def delete_active_profile() -> None:
    """Remove the persisted profile (for logout/reset)."""
    if ACTIVE_PROFILE_FILE.exists():
        ACTIVE_PROFILE_FILE.unlink()


def has_saved_profile() -> bool:
    """Check if a profile has been saved (fast check, no full load)."""
    return ACTIVE_PROFILE_FILE.exists()
