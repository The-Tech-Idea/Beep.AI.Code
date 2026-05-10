"""Code block detection and highlighting."""

from __future__ import annotations

from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.lexers.special import TextLexer

LANGUAGE_ALIASES = {
    "ts": "typescript",
    "js": "javascript",
    "py": "python",
    "rb": "ruby",
    "rs": "rust",
    "cs": "csharp",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "md": "markdown",
    "yml": "yaml",
    "tf": "hcl",
    "dockerfile": "docker",
}

formatter = TerminalTrueColorFormatter(style="monokai")


def highlight_code(code: str, language: str = "text") -> str:
    """Highlight code using Pygments.

    Args:
        code: Source code to highlight
        language: Language name or alias

    Returns:
        Highlighted code string for terminal display
    """
    lang = LANGUAGE_ALIASES.get(language.lower(), language.lower())

    try:
        lexer = get_lexer_by_name(lang)
    except Exception:
        lexer = TextLexer()

    return str(highlight(code, lexer, formatter).rstrip())


def highlight_file(content: str, filename: str) -> str:
    """Highlight code based on filename.

    Args:
        content: Source code
        filename: File path or name

    Returns:
        Highlighted code string
    """
    try:
        lexer = get_lexer_for_filename(filename)
    except Exception:
        lexer = TextLexer()

    return str(highlight(content, lexer, formatter).rstrip())
