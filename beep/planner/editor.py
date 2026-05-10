"""Multi-file editing and planning system.

Enables the agent to:
- Create a plan before executing changes
- Edit multiple files in a single request
- Show a summary of all changes before applying
- Rollback changes if something goes wrong
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from beep.workspace.file_ops import create_diff, write_file



from beep.utils.console import get_console
class PlanStatus(Enum):
    """Status of an edit plan."""

    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class FileEdit:
    """A single file edit operation."""

    file_path: Path
    old_content: str = ""
    new_content: str = ""
    applied: bool = False
    backup_path: Path | None = None

    @property
    def diff(self) -> str:
        return create_diff(self.old_content, self.new_content, str(self.file_path))

    @property
    def is_create(self) -> bool:
        return not self.file_path.exists()

    @property
    def is_delete(self) -> bool:
        return not self.new_content and self.file_path.exists()


@dataclass
class EditPlan:
    """A plan for editing multiple files."""

    goal: str
    edits: list[FileEdit] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    notes: str = ""

    def add_edit(self, file_path: Path, old_content: str, new_content: str) -> None:
        """Add an edit to the plan."""
        self.edits.append(FileEdit(
            file_path=file_path,
            old_content=old_content,
            new_content=new_content,
        ))

    def display(self) -> None:
        """Display the plan summary."""
        get_console().print(Panel(
            f"[bold]Goal:[/bold] {self.goal}\n"
            f"[bold]Files to change:[/bold] {len(self.edits)}\n"
            f"[bold]Status:[/bold] {self.status.value}",
            title="Edit Plan",
            border_style="blue",
        ))

        table = Table(title="File Changes")
        table.add_column("File", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Lines Changed", justify="right")

        for edit in self.edits:
            if edit.is_create:
                change_type = "CREATE"
                lines = len(edit.new_content.splitlines())
            elif edit.is_delete:
                change_type = "DELETE"
                lines = len(edit.old_content.splitlines())
            else:
                change_type = "EDIT"
                diff_lines = edit.diff.count("\n")
                lines = diff_lines // 2

            table.add_row(
                str(edit.file_path),
                change_type,
                str(lines),
            )

        get_console().print(table)

    async def execute(self, require_confirm: bool = True) -> bool:
        """Execute all edits in the plan."""
        if require_confirm:
            self.display()
            from rich.prompt import Confirm
            if not Confirm.ask("Apply all changes?"):
                get_console().print("[yellow]Plan cancelled[/yellow]")
                return False

        self.status = PlanStatus.IN_PROGRESS

        for edit in self.edits:
            try:
                if edit.is_create:
                    write_file(edit.file_path, edit.new_content)
                    edit.applied = True
                elif edit.is_delete:
                    edit.backup_path = edit.file_path.with_suffix(
                        edit.file_path.suffix + ".deleted"
                    )
                    edit.file_path.rename(edit.backup_path)
                    edit.applied = True
                else:
                    edit.file_path.write_text(edit.new_content, encoding="utf-8")
                    edit.applied = True
            except Exception as exc:
                get_console().print(f"[red]Failed to edit {edit.file_path}: {e}[/red]")
                await self.rollback()
                self.status = PlanStatus.FAILED
                return False

        self.status = PlanStatus.COMPLETED
        get_console().print(f"[green]Applied {len(self.edits)} changes[/green]")
        return True

    async def rollback(self) -> None:
        """Rollback all applied edits."""
        for edit in reversed(self.edits):
            if not edit.applied:
                continue

            try:
                if edit.is_create and edit.file_path.exists():
                    edit.file_path.unlink()
                elif edit.is_delete and edit.backup_path and edit.backup_path.exists():
                    edit.backup_path.rename(edit.file_path)
                else:
                    edit.file_path.write_text(edit.old_content, encoding="utf-8")
            except Exception as exc:
                get_console().print(f"[red]Rollback failed for {edit.file_path}: {e}[/red]")

        self.status = PlanStatus.ROLLED_BACK
        get_console().print("[yellow]All changes rolled back[/yellow]")


PLAN_PROMPT = """When making changes to multiple files, follow this process:

1. First, read all relevant files to understand the current state
2. Create a plan listing all files you want to change and what changes you'll make
3. Show the plan to the user for approval
4. Apply all changes at once
5. Verify the changes work (run tests if applicable)

Format your plan as:

PLAN: <goal description>
- FILE: <path>
  <new content or description of changes>
- FILE: <path>
  <new content or description of changes>
...
"""
