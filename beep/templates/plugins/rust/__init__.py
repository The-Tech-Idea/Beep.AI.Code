"""Rust project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_rust_library_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="rust-library",
        language="rust",
        description="Rust library crate.",
        files=[
            TemplateFile(path="Cargo.toml"),
            TemplateFile(path="src/lib.rs"),
            TemplateFile(path="tests/integration_test.rs", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="cargo build",
        test_command="cargo test",
        lint_command="cargo clippy",
        tags=["library", "crate"],
        recommended_tools=["clippy", "rustfmt"],
    )


def get_rust_cli_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="rust-cli",
        language="rust",
        framework="cli",
        description="Rust command-line application.",
        files=[
            TemplateFile(path="Cargo.toml"),
            TemplateFile(path="src/main.rs"),
            TemplateFile(path="src/cli.rs", required=False),
            TemplateFile(path="tests/cli_test.rs", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="cargo build",
        test_command="cargo test",
        run_command="cargo run",
        lint_command="cargo clippy",
        tags=["cli", "application"],
        recommended_tools=["clippy", "rustfmt", "clap"],
    )
