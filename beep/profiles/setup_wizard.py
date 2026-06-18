"""Profile-driven setup wizard — calls Simple Service Generator on the server.

This replaces the old text-based setup wizard with a profile-driven flow:
1. Detect hardware (from server)
2. Pick a profile
3. Answer 2-4 plain-language questions
4. Preview → Create All
5. Save profile locally → skip wizard on restart
"""

from __future__ import annotations

import asyncio
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from beep.config import BeepConfig, load_config, save_config
from beep.profiles import (
    UserProfile,
    has_saved_profile,
    load_active_profile,
    save_active_profile,
)
from beep.profiles.server_bridge import (
    create_batch_and_save_profile,
    list_available_profiles,
    preview_batch,
    poll_batch_progress,
)
from beep.profiles.startup import apply_profile_to_config

PROFILE_DISPLAY: dict[str, dict[str, str]] = {
    "team_lead_dev": {
        "name": "Team Lead (Development)",
        "icon": "👥",
        "description": "Coding assistants for your development team",
    },
    "business_analyst": {
        "name": "Business Analyst",
        "icon": "📊",
        "description": "Search and analyze your documents",
    },
    "team_lead_biz": {
        "name": "Team Lead (Business)",
        "icon": "💼",
        "description": "AI assistants for non-coding work",
    },
    "content_creator": {
        "name": "Content Creator",
        "icon": "✍️",
        "description": "Generate images, voice, and designs",
    },
    "student": {
        "name": "Student / Hobbyist",
        "icon": "🎓",
        "description": "Learning and experimenting with AI",
    },
    "developer": {
        "name": "Developer",
        "icon": "💻",
        "description": "Full control — all services and settings",
    },
}


def run_profile_setup_wizard(
    server_url: str = "http://localhost:5000",
    api_token: str | None = None,
) -> UserProfile | None:
    """Run the profile-driven setup wizard.

    Returns the saved UserProfile, or None if cancelled.
    """
    console = Console()
    console.print()
    console.print(Panel.fit(
        "[bold]Welcome to Beep.AI![/bold]\n\n"
        "Let's set up your AI experience in 3 simple steps.\n"
        "No technical knowledge needed.",
        title="Beep.AI Setup",
    ))
    console.print()

    # Step 1: Pick a profile
    profile_id = _pick_profile(console, server_url)
    if profile_id is None:
        return None

    display = PROFILE_DISPLAY.get(profile_id, {})
    profile_name = display.get("name", profile_id)
    profile_icon = display.get("icon", "🤖")

    # Step 2: Answer questions
    answers = _ask_questions(console, profile_id)
    if answers is None:
        return None

    # Step 3: Preview and create
    return asyncio.run(
        _create_and_save(
            console,
            server_url,
            profile_id,
            profile_name,
            profile_icon,
            answers,
            api_token,
        )
    )


def _pick_profile(console: Console, server_url: str) -> str | None:
    """Show available profiles and let user pick one."""
    console.print("[bold]Step 1: What do you want to do?[/bold]")
    console.print()

    # Try to get profiles from server
    try:
        server_profiles = asyncio.run(list_available_profiles(server_url))
        available = server_profiles.get("profiles", [])
        dimmed = server_profiles.get("dimmed", [])
        hardware_label = server_profiles.get("hardware_label", "")
        if hardware_label:
            console.print(f"[dim]🖥  {hardware_label}[/dim]")
            console.print()
    except Exception:
        available = []
        dimmed = []

    if available:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("#", style="dim")
        table.add_column("Profile")
        for i, p in enumerate(available, 1):
            pid = p.get("profile_id", "")
            info = PROFILE_DISPLAY.get(pid, {})
            table.add_row(
                str(i),
                f"{info.get('icon', '🤖')} [bold]{info.get('name', pid)}[/bold]\n"
                f"   [dim]{info.get('description', '')}[/dim]",
            )
        console.print(table)
    else:
        # Fallback: show built-in profiles
        for pid, info in PROFILE_DISPLAY.items():
            console.print(f"  {info['icon']} [bold]{info['name']}[/bold] — [dim]{info['description']}[/dim]")

    console.print()
    choices = list(PROFILE_DISPLAY.keys())
    choice_map = {str(i + 1): pid for i, pid in enumerate(choices)}

    try:
        answer = Prompt.ask(
            "Enter a number (or profile ID)",
            choices=list(choice_map.keys()) + choices,
            default="1",
        )
    except (KeyboardInterrupt, EOFError):
        return None

    if answer in choice_map:
        return choice_map[answer]
    if answer in choices:
        return answer
    return choices[0]


def _ask_questions(console: Console, profile_id: str) -> dict[str, Any] | None:
    """Ask profile-specific questions."""
    questions: dict[str, dict[str, Any]] = {
        "team_lead_dev": {
            "framework": {
                "text": "What's your team building with?",
                "choices": ["react", "vue", "blazor", "wpf", "flask", "django", "fastapi"],
                "default": "react",
            },
            "coding_extras": {
                "text": "Would you also like code review, bug finding, or test writing?",
                "choices": ["all", "code_reviewer", "bug_fixer", "test_writer", "none"],
                "default": "all",
                "multi": True,
            },
        },
        "business_analyst": {
            "document_type": {
                "text": "What kind of documents do you want to search?",
                "choices": ["pdfs_docs", "spreadsheets", "emails", "web", "all"],
                "default": "all",
            },
            "storage_location": {
                "text": "Where are they stored?",
                "choices": ["local", "network", "cloud"],
                "default": "local",
            },
        },
        "team_lead_biz": {
            "industry": {
                "text": "What industry are you in?",
                "choices": ["legal", "office", "ecommerce", "oil_gas", "business_analysis"],
                "default": "legal",
            },
        },
        "content_creator": {
            "content_types": {
                "text": "What kind of content do you create?",
                "choices": ["images", "voice", "designs", "all"],
                "default": "all",
                "multi": True,
            },
        },
        "student": {
            "student_goal": {
                "text": "What do you want to try?",
                "choices": ["chat", "search", "both"],
                "default": "both",
            },
        },
    }

    profile_questions = questions.get(profile_id, {})
    if not profile_questions:
        console.print("[dim]No questions needed — setting up with defaults.[/dim]")
        return {}

    console.print()
    console.print("[bold]Step 2: A few quick questions[/bold]")
    console.print()

    answers: dict[str, Any] = {}
    try:
        for qid, q in profile_questions.items():
            if q.get("multi"):
                choices_str = "/".join(q["choices"])
                answer = Prompt.ask(
                    f"  {q['text']} [{choices_str}]",
                    default=q["default"],
                )
                if answer.lower() == "all":
                    answers[qid] = q["choices"][:-1]  # All except "all" and "none"
                elif answer.lower() == "none":
                    answers[qid] = []
                else:
                    answers[qid] = [a.strip() for a in answer.split(",") if a.strip()]
            else:
                answer = Prompt.ask(
                    f"  {q['text']}",
                    choices=q["choices"],
                    default=q["default"],
                )
                answers[qid] = answer
    except (KeyboardInterrupt, EOFError):
        return None

    return answers


async def _create_and_save(
    console: Console,
    server_url: str,
    profile_id: str,
    profile_name: str,
    profile_icon: str,
    answers: dict[str, Any],
    api_token: str | None,
) -> UserProfile | None:
    """Preview, confirm, create, and save."""
    console.print()
    console.print("[bold]Step 3: Review and create[/bold]")
    console.print()

    # Preview
    try:
        preview = await preview_batch(server_url, profile_id, answers)
        console.print(
            f"  [bold]{preview.get('total_services', 0)} services[/bold] will be created "
            f"(~{preview.get('estimated_minutes', 0)} minutes, "
            f"~{preview.get('total_download_gb', 0)} GB download)"
        )
        console.print()
        services = preview.get("service_names", [])
        for svc in services:
            console.print(f"    ✅ {svc}")
        console.print()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not preview: {e}[/yellow]")
        console.print("[dim]Continuing anyway...[/dim]")
        console.print()

    # Confirm
    try:
        answer = Prompt.ask("Create these services now?", choices=["y", "n"], default="y")
    except (KeyboardInterrupt, EOFError):
        return None

    if answer.lower() != "y":
        console.print("[yellow]Setup cancelled. Run 'beep setup-profile' to try again.[/yellow]")
        return None

    # Create
    console.print()
    console.print("[bold]Creating your AI experience...[/bold]")
    console.print()

    try:
        batch_id, profile = await create_batch_and_save_profile(
            server_url=server_url,
            profile_id=profile_id,
            profile_display_name=profile_name,
            profile_icon=profile_icon,
            answers=answers,
            api_token=api_token,
        )

        # Apply to config
        apply_profile_to_config(profile)

        # Poll progress with simple spinner
        import time
        with console.status("[bold green]Setting up...[/bold green]") as status:
            for _ in range(60):  # Max 60 seconds
                try:
                    progress = await poll_batch_progress(server_url, batch_id, api_token)
                    pct = progress.get("overall_progress_pct", 0)
                    step = progress.get("current_step", "")
                    status.update(f"[bold green]Setting up... {pct}%[/bold green] {step}")
                    if progress.get("status") in ("done", "paused_on_error"):
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)

        console.print()
        console.print(Panel.fit(
            f"[bold green]✅ All set![/bold green]\n\n"
            f"Your {profile_name} experience is ready.\n"
            f"Next time you run Beep.AI, you'll skip straight to your workspace.",
            title="Setup Complete",
        ))
        console.print()

        return profile

    except Exception as e:
        console.print(f"[red]❌ Setup failed: {e}[/red]")
        console.print("[yellow]Run 'beep setup-profile' to try again.[/yellow]")
        return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def setup_profile_command() -> None:
    """CLI command: beep setup-profile"""
    console = Console()

    # Check if profile already exists
    if has_saved_profile():
        profile = load_active_profile()
        if profile:
            console.print(f"[dim]Profile already set: {profile.profile_display_name}[/dim]")
            console.print("[dim]Run 'beep setup-profile --reset' to start over.[/dim]")
            return

    config = load_config()
    server_url = config.server_url or "http://localhost:5000"
    api_token = config.api_token

    console.print("[dim]Checking server connection...[/dim]")

    try:
        import httpx
        resp = httpx.get(f"{server_url.rstrip('/')}/api/health", timeout=5.0)
        if resp.status_code == 200:
            console.print("[green]✅ Server is running[/green]")
        else:
            console.print(f"[yellow]⚠ Server responded with status {resp.status_code}[/yellow]")
    except Exception:
        console.print("[red]❌ Cannot reach Beep.AI.Server[/red]")
        console.print(f"[dim]Make sure the server is running at {server_url}[/dim]")
        console.print("[dim]Run 'beep setup' to configure connection manually.[/dim]")
        return

    profile = run_profile_setup_wizard(server_url, api_token)
    if profile is None:
        console.print("[yellow]Profile setup cancelled.[/yellow]")
