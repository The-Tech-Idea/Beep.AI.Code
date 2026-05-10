"""Python project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_python_library_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="python-library",
        language="python",
        description="Standard Python library package.",
        files=[
            TemplateFile(path="pyproject.toml", description="Build config."),
            TemplateFile(path="src/{{name}}/__init__.py"),
            TemplateFile(path="tests/__init__.py"),
            TemplateFile(path="tests/test_main.py"),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="pip install -e .",
        test_command="pytest",
        lint_command="ruff check .",
        tags=["library", "package"],
        recommended_tools=["ruff", "pytest"],
    )


def get_python_cli_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="python-cli",
        language="python",
        framework="cli",
        description="Python command-line application.",
        files=[
            TemplateFile(path="pyproject.toml", description="Build config with console_scripts."),
            TemplateFile(path="src/{{name}}/__init__.py"),
            TemplateFile(path="src/{{name}}/cli.py", description="CLI entry point."),
            TemplateFile(path="tests/__init__.py"),
            TemplateFile(path="tests/test_cli.py"),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="pip install -e .",
        test_command="pytest",
        run_command="{{name}}",
        lint_command="ruff check .",
        tags=["cli", "application"],
        recommended_tools=["ruff", "pytest", "click"],
    )


def get_python_webapp_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="python-webapp",
        language="python",
        framework="fastapi",
        description="FastAPI web application.",
        files=[
            TemplateFile(path="pyproject.toml", description="Build config."),
            TemplateFile(path="src/{{name}}/__init__.py"),
            TemplateFile(path="src/{{name}}/main.py", description="FastAPI app entry point."),
            TemplateFile(path="src/{{name}}/routes/__init__.py"),
            TemplateFile(path="tests/__init__.py"),
            TemplateFile(path="tests/test_api.py"),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="pip install -e .",
        test_command="pytest",
        run_command="uvicorn {{name}}.main:app --reload",
        lint_command="ruff check .",
        tags=["web", "api", "fastapi"],
        recommended_tools=["ruff", "pytest", "uvicorn", "fastapi"],
    )
