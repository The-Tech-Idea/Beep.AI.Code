"""Fine-grained permissions and safety system.

Controls what the agent can do based on:
- Trust levels per directory
- Tool-specific permissions
- Auto-approve rules for safe operations
- Dangerous operation guards
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TrustLevel(Enum):
    """Trust level for a directory."""

    FULL = "full"
    READ_ONLY = "read_only"
    ASK = "ask"
    DENIED = "denied"


class SandboxMode(Enum):
    """Canonical runtime sandbox modes for chat and agent flows."""

    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    FULL_TRUST = "full-trust"


class RiskLevel(Enum):
    """Risk level for an operation."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DESTRUCTIVE = "destructive"


@dataclass
class PermissionRule:
    """A permission rule for a tool or operation."""

    tool_name: str
    risk: RiskLevel
    auto_approve: bool = False
    description: str = ""


@dataclass(frozen=True)
class PermissionDecision:
    """Resolved permission policy for one tool invocation."""

    allowed: bool
    requires_approval: bool
    reason: str


def coerce_sandbox_mode(value: SandboxMode | str | bool | None) -> SandboxMode:
    """Normalize CLI/chat sandbox inputs to a canonical mode."""
    if isinstance(value, SandboxMode):
        return value
    if isinstance(value, bool):
        return SandboxMode.READ_ONLY if value else SandboxMode.WORKSPACE_WRITE

    raw = str(value or "").strip().lower().replace("_", "-")
    if raw in {"", SandboxMode.WORKSPACE_WRITE.value, "workspace", "off", "default"}:
        return SandboxMode.WORKSPACE_WRITE
    if raw in {SandboxMode.READ_ONLY.value, "readonly", "read only", "on"}:
        return SandboxMode.READ_ONLY
    if raw in {SandboxMode.FULL_TRUST.value, "full", "trusted", "unsafe"}:
        return SandboxMode.FULL_TRUST

    allowed = ", ".join(mode.value for mode in SandboxMode)
    raise ValueError(f"Unknown sandbox mode '{value}'. Use one of: {allowed}.")


@dataclass
class TrustZone:
    """Trust configuration for a directory."""

    path: Path
    level: TrustLevel = TrustLevel.ASK
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)


class PermissionManager:
    """Manages permissions and safety checks."""

    DEFAULT_RULES: list[PermissionRule] = [
        PermissionRule("file_read", RiskLevel.SAFE, auto_approve=True, description="Read files"),
        PermissionRule("read_files", RiskLevel.SAFE, auto_approve=True, description="Read multiple files"),
        PermissionRule("context", RiskLevel.SAFE, auto_approve=True, description="Read project context"),
        PermissionRule("search", RiskLevel.SAFE, auto_approve=True, description="Search files"),
        PermissionRule("list_directory", RiskLevel.SAFE, auto_approve=True, description="List directories"),
        PermissionRule("glob_files", RiskLevel.SAFE, auto_approve=True, description="Glob workspace files"),
        PermissionRule("file_write", RiskLevel.MEDIUM, description="Create/overwrite files"),
        PermissionRule("file_edit", RiskLevel.MEDIUM, description="Edit files"),
        PermissionRule("single_edit", RiskLevel.MEDIUM, description="Edit files with search/replace"),
        PermissionRule("python_rename", RiskLevel.MEDIUM, description="Rename Python symbols"),
        PermissionRule("git", RiskLevel.MEDIUM, description="Run git commands"),
        PermissionRule("shell", RiskLevel.HIGH, description="Execute shell commands"),
    ]

    DANGEROUS_COMMANDS = [
        "rm -rf", "rm -f", "del /s", "rmdir /s",
        "format", "mkfs", "dd if=",
        "shutdown", "reboot", "kill -9",
        "> /dev/", "> /etc/", "> /boot/",
        "chmod 777", "chown root",
    ]

    def __init__(self) -> None:
        self._rules = {
            r.tool_name: PermissionRule(
                tool_name=r.tool_name,
                risk=r.risk,
                auto_approve=r.auto_approve,
                description=r.description,
            )
            for r in self.DEFAULT_RULES
        }
        self._trust_zones: list[TrustZone] = []
        self._denied_paths: list[Path] = [
            Path("/etc"),
            Path("/boot"),
            Path("/dev"),
            Path("/proc"),
            Path("/sys"),
        ]

    def add_trust_zone(self, zone: TrustZone) -> None:
        """Add a trust zone."""
        self._trust_zones.append(zone)

    def add_denied_path(self, path: Path) -> None:
        """Add a denied path."""
        if path not in self._denied_paths:
            self._denied_paths.append(path)

    def set_rule(self, tool_name: str, auto_approve: bool) -> None:
        """Set auto-approve for a tool."""
        if tool_name in self._rules:
            self._rules[tool_name].auto_approve = auto_approve

    def has_rule(self, tool_name: str) -> bool:
        """Return whether the manager has an explicit rule for this tool."""
        return tool_name in self._rules

    def evaluate_permission(
        self,
        tool_name: str,
        arguments: dict,
        workspace_root: Path,
        *,
        sandbox_mode: SandboxMode | str | bool | None = SandboxMode.WORKSPACE_WRITE,
    ) -> PermissionDecision:
        """Resolve whether a tool call is allowed, approval-gated, or blocked."""
        mode = coerce_sandbox_mode(sandbox_mode)
        rule = self._rules.get(tool_name)
        if not rule:
            return PermissionDecision(False, False, f"Unknown tool: {tool_name}")

        if tool_name == "shell":
            return self._check_shell_command(arguments, workspace_root, mode)

        if tool_name == "git":
            return self._check_git_operation(arguments, workspace_root, mode)

        if tool_name in {"file_write", "file_edit", "single_edit", "python_rename"}:
            return self._check_file_operation(arguments, workspace_root, tool_name, mode)

        return PermissionDecision(True, False, "Auto-approved")

    def check_permission(
        self,
        tool_name: str,
        arguments: dict,
        workspace_root: Path,
    ) -> tuple[bool, str]:
        """Check if an operation is permitted.

        Returns:
            (allowed, reason)
        """
        decision = self.evaluate_permission(tool_name, arguments, workspace_root)
        if decision.allowed and not decision.requires_approval:
            return True, decision.reason or "Auto-approved"
        if decision.allowed:
            return False, decision.reason or "Requires approval"
        return False, decision.reason

    def _check_shell_command(
        self,
        arguments: dict,
        workspace_root: Path,
        sandbox_mode: SandboxMode,
    ) -> PermissionDecision:
        """Check if a shell command is safe."""
        command = arguments.get("command", "")

        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command.lower():
                return PermissionDecision(False, False, f"Dangerous command detected: {dangerous}")

        trust_level = self.get_trust_level(workspace_root)
        if trust_level == TrustLevel.DENIED:
            return PermissionDecision(False, False, "Trust zone denies shell execution in this workspace")
        if sandbox_mode == SandboxMode.READ_ONLY or trust_level == TrustLevel.READ_ONLY:
            return PermissionDecision(False, False, "Sandbox mode blocks shell execution")
        if sandbox_mode == SandboxMode.FULL_TRUST or trust_level == TrustLevel.FULL:
            return PermissionDecision(True, False, "Sandbox mode allows shell execution")

        return PermissionDecision(True, True, "Shell commands require approval")

    def _check_file_operation(
        self,
        arguments: dict,
        workspace_root: Path,
        tool_name: str,
        sandbox_mode: SandboxMode,
    ) -> PermissionDecision:
        """Check if a file operation is within allowed paths."""
        file_path = arguments.get("file_path", "")
        if not file_path:
            return PermissionDecision(False, False, f"{tool_name} requires file_path")
        target = Path(file_path).resolve()

        for denied in self._denied_paths:
            try:
                target.relative_to(denied)
                return PermissionDecision(False, False, f"Path denied: {denied}")
            except ValueError:
                pass

        try:
            target.relative_to(workspace_root.resolve())
        except ValueError:
            return PermissionDecision(False, False, "File outside workspace is blocked by sandbox policy")

        trust_level = self.get_trust_level(target)
        if trust_level == TrustLevel.DENIED:
            return PermissionDecision(False, False, f"Trust zone denies access to {target}")
        if sandbox_mode == SandboxMode.READ_ONLY or trust_level == TrustLevel.READ_ONLY:
            return PermissionDecision(False, False, f"Sandbox mode blocks {tool_name}")
        if sandbox_mode == SandboxMode.FULL_TRUST or trust_level == TrustLevel.FULL:
            return PermissionDecision(True, False, "Sandbox mode allows file mutation")

        rule = self._rules.get(tool_name)
        if rule and rule.auto_approve:
            return PermissionDecision(True, False, "Auto-approved")

        return PermissionDecision(True, True, f"{tool_name} requires approval")

    def _check_git_operation(
        self,
        arguments: dict,
        workspace_root: Path,
        sandbox_mode: SandboxMode,
    ) -> PermissionDecision:
        subcommand = str(arguments.get("subcommand", "")).strip()
        trust_level = self.get_trust_level(workspace_root)
        if trust_level == TrustLevel.DENIED:
            return PermissionDecision(False, False, "Trust zone denies git operations in this workspace")

        if not subcommand:
            if sandbox_mode == SandboxMode.READ_ONLY or trust_level == TrustLevel.READ_ONLY:
                return PermissionDecision(False, False, "Ambiguous git command blocked in read-only mode")
            if sandbox_mode == SandboxMode.FULL_TRUST or trust_level == TrustLevel.FULL:
                return PermissionDecision(True, False, "Sandbox mode allows git mutation")
            return PermissionDecision(True, True, "Git command requires approval")

        verb = subcommand.split()[0].lower()
        if verb in {"status", "diff", "log", "show"}:
            return PermissionDecision(True, False, "Auto-approved")

        if sandbox_mode == SandboxMode.READ_ONLY or trust_level == TrustLevel.READ_ONLY:
            return PermissionDecision(False, False, "Sandbox mode blocks git mutations")
        if sandbox_mode == SandboxMode.FULL_TRUST or trust_level == TrustLevel.FULL:
            return PermissionDecision(True, False, "Sandbox mode allows git mutation")
        return PermissionDecision(True, True, "Git mutation requires approval")

    def get_trust_level(self, path: Path) -> TrustLevel:
        """Get trust level for a path."""
        for zone in sorted(
            self._trust_zones,
            key=lambda z: len(str(z.path)),
            reverse=True,
        ):
            try:
                path.resolve().relative_to(zone.path.resolve())
                return zone.level
            except ValueError:
                continue

        return TrustLevel.ASK

    def to_prompt_section(self) -> str:
        """Generate a permissions info section for the system prompt."""
        lines = ["## Permissions & Safety", ""]
        lines.append("You must ask for approval before:")
        for name, rule in self._rules.items():
            if not rule.auto_approve:
                lines.append(f"- {name}: {rule.description}")

        lines.append("")
        lines.append("You cannot access system directories (/etc, /boot, /dev, etc.)")
        lines.append("Dangerous commands (rm -rf, format, etc.) are blocked.")

        return "\n".join(lines)
