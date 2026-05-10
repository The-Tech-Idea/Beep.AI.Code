# beep.spec — PyInstaller build spec for Beep.AI.Code
# Usage: pyinstaller beep.spec --clean
# Output: dist/beep  (or dist/beep.exe on Windows)

import sys
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

block_cipher = None
ROOT = Path(SPECPATH)

# Hidden imports from dynamic plugin/command discovery
HIDDEN_IMPORTS = [
    # Core CLI
    "beep.cli",
    "beep.cli_support",
    "beep.cli_support_async",
    "beep.cli_defaults",
    "beep.cli_command_registration",
    "beep.config",
    "beep.app_service",
    # Commands
    "beep.commands.agent",
    "beep.commands.agent_admin",
    "beep.commands.agent_bundle",
    "beep.commands.agent_deploy",
    "beep.commands.agent_inputs",
    "beep.commands.agent_package",
    "beep.commands.agent_status_support",
    "beep.commands.chat",
    "beep.commands.ask",
    "beep.commands.review",
    "beep.commands.self_update",
    "beep.commands.diagnostics_runtime_support",
    "beep.commands.diagnostics_schema_support",
    # Agent
    "beep.agent.loop",
    "beep.agent.environment",
    "beep.agent.environment_catalog",
    "beep.agent.provider_plugins",
    "beep.agent.bundle_store",
    "beep.agent.bundle_contract",
    # API / transport
    "beep.api.client",
    "beep.mcp.discovery",
    "beep.mcp.client",
    "beep.mcp.live_discovery",
    "beep.mcp.http_transport",
    # Runtime
    "beep.runtime.workspace",
    "beep.workspace.detector",
    "beep.plugins.runtime",
    "beep.permissions.manager",
    "beep.setup_wizard",
    "beep.setup_wizard_flows",
    "beep.setup_wizard_support",
    # Rich / Textual internals resolved lazily
    "rich.console",
    "rich.table",
    "rich.panel",
    "rich.progress",
    "textual.app",
    # keyring backends
    "keyring.backends",
    "keyring.backends.fail",
    "keyring.backends.SecretService",
    "keyring.backends.kwallet",
]

a = Analysis(
    [str(ROOT / "beep" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "completions"), "completions"),
    ],
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "mypy",
        "ruff",
        "IPython",
        "jupyter",
        "notebook",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "cv2",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="beep",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
