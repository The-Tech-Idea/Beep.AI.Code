"""Profile-aware chat augmentation.

Builds welcome banners, system prompts, and context enriched
with the user's profile settings.
"""

from __future__ import annotations

from beep.profiles import UserProfile, has_saved_profile, load_active_profile


def get_active_profile() -> UserProfile | None:
    """Return the currently active profile, or None."""
    if not has_saved_profile():
        return None
    return load_active_profile()


def build_welcome_banner(profile: UserProfile | None = None) -> str:
    """Build a profile-aware welcome message for the chat REPL."""
    if profile is None:
        profile = get_active_profile()

    if profile is None:
        return (
            "[bold]Welcome to Beep.AI.Code[/bold]\n\n"
            "Type [bold]/help[/bold] for available commands.\n"
            "Run [bold]beep setup-profile[/bold] to set up your AI experience."
        )

    return (
        f"{profile.profile_icon} [bold]Welcome back, {profile.profile_display_name}[/bold]\n\n"
        f"Profile configured for [bold]{profile.profile_id}[/bold].\n"
        f"Model: [dim]{profile.model.model_id}[/dim]  |  "
        f"Server: [dim]{profile.server_url}[/dim]\n\n"
        "Type [bold]/help[/bold] for available commands."
    )


def build_profile_system_prompt(profile: UserProfile | None = None) -> str:
    """Build a profile-specific system prompt augmentation.

    Returns additional instructions based on the user's profile
    that get appended to the base system prompt.
    """
    if profile is None:
        profile = get_active_profile()
    if profile is None:
        return ""

    augmentations: dict[str, str] = {
        "team_lead_dev": (
            "You are assisting a development team lead. The user manages a team "
            "of developers. Focus on code quality, architecture decisions, "
            "team productivity, and best practices. Reference specific files "
            "and line numbers when reviewing code. Suggest patterns and "
            "refactoring approaches appropriate for team-scale projects."
        ),
        "business_analyst": (
            "You are assisting a business analyst. The user works with documents, "
            "spreadsheets, and reports. Focus on data analysis, document search, "
            "and extracting insights. When referencing documents, cite specific "
            "sections or pages. Help find connections between different data sources."
        ),
        "team_lead_biz": (
            "You are assisting a business team lead. Focus on industry-specific "
            "knowledge, document review, contract analysis, and business process "
            "optimization. Use professional but accessible language."
        ),
        "content_creator": (
            "You are assisting a content creator. Focus on creative work — "
            "image generation, voice synthesis, design feedback, and content "
            "strategy. Be visual and descriptive in your responses."
        ),
        "student": (
            "You are assisting a student or learner. Use simple, clear language. "
            "Explain concepts thoroughly. Offer to simplify or elaborate on "
            "any explanation. Be encouraging and patient."
        ),
        "solo_founder": (
            "You are assisting a startup founder building a product. Focus on "
            "rapid prototyping, full-stack development, and shipping features. "
            "Suggest practical, iterative approaches. Prioritize working code "
            "over perfect architecture."
        ),
    }

    return augmentations.get(profile.profile_id, "")


def build_context_hint(profile: UserProfile | None = None) -> str:
    """Build a one-line hint about the active profile for the status bar."""
    if profile is None:
        profile = get_active_profile()
    if profile is None:
        return "[dim]No profile[/dim]"

    return (
        f"{profile.profile_icon} [bold]{profile.profile_display_name}[/bold]"
        f"  |  [dim]{profile.model.model_id}[/dim]"
        f"  |  [dim]{profile.server_url}[/dim]"
    )
