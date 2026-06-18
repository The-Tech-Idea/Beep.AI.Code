"""LSP server registry — maps languages to known LSP server commands."""

from __future__ import annotations

from pathlib import Path

LANGUAGE_SERVERS: dict[str, list[list[str]]] = {
    "python": [["pyright-langserver", "--stdio"], ["pylsp", "--stdio"]],
    "typescript": [["typescript-language-server", "--stdio"]],
    "typescriptreact": [["typescript-language-server", "--stdio"]],
    "javascript": [["typescript-language-server", "--stdio"]],
    "javascriptreact": [["typescript-language-server", "--stdio"]],
    "rust": [["rust-analyzer"]],
    "go": [["gopls"]],
    "java": [["jdtls"]],
    "csharp": [["omnisharp", "--languageserver"]],
    "c": [["clangd"]],
    "cpp": [["clangd"]],
    "ruby": [["solargraph", "stdio"]],
    "swift": [["sourcekit-lsp"]],
    "kotlin": [["kotlin-language-server"]],
    "vue": [["vue-language-server", "--stdio"]],
    "svelte": [["svelteserver", "--stdio"]],
    "json": [["vscode-json-languageserver", "--stdio"]],
    "yaml": [["yaml-language-server", "--stdio"]],
    "css": [["vscode-css-languageserver", "--stdio"]],
    "html": [["vscode-html-languageserver", "--stdio"]],
    "sql": [["sql-language-server", "up", "--method", "stdio"]],
}


def find_server_command(file_path: Path) -> list[str] | None:
    import shutil

    ext = file_path.suffix.lower()
    if ext == ".py":
        lang = "python"
    else:
        from beep.lsp.client import _guess_language as guess_lang

        lang = guess_lang(file_path)

    candidates = LANGUAGE_SERVERS.get(lang, [])
    for cmd in candidates:
        if shutil.which(cmd[0]):
            return cmd
    return None


def available_languages() -> list[str]:
    return sorted(LANGUAGE_SERVERS.keys())
