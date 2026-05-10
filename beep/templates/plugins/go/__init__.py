"""Go project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_go_cli_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="go-cli",
        language="go",
        framework="cli",
        description="Go command-line application.",
        files=[
            TemplateFile(path="go.mod"),
            TemplateFile(path="main.go"),
            TemplateFile(path="cmd/root.go", required=False),
            TemplateFile(path="pkg/{{name}}/{{name}}.go", required=False),
            TemplateFile(path="tests/main_test.go", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="go build",
        test_command="go test ./...",
        run_command="./{{name}}",
        lint_command="golangci-lint run",
        tags=["cli", "application"],
        recommended_tools=["golangci-lint"],
    )


def get_go_webapi_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="go-webapi",
        language="go",
        framework="gin",
        description="Go web API with Gin.",
        files=[
            TemplateFile(path="go.mod"),
            TemplateFile(path="main.go"),
            TemplateFile(path="handlers/handler.go", required=False),
            TemplateFile(path="middleware/middleware.go", required=False),
            TemplateFile(path="tests/handler_test.go", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="go build",
        test_command="go test ./...",
        run_command="go run main.go",
        lint_command="golangci-lint run",
        tags=["web", "api", "gin"],
        recommended_tools=["golangci-lint", "gin"],
    )
