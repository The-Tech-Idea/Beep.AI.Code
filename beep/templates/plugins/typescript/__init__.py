"""TypeScript project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_ts_library_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="ts-library",
        language="typescript",
        description="TypeScript library package.",
        files=[
            TemplateFile(path="package.json"),
            TemplateFile(path="tsconfig.json"),
            TemplateFile(path="src/index.ts"),
            TemplateFile(path="tests/index.test.ts", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="npx tsc",
        test_command="npm test",
        lint_command="npx eslint .",
        tags=["library", "npm", "typescript"],
        recommended_tools=["eslint", "jest", "typescript"],
    )


def get_ts_nodeapp_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="ts-nodeapp",
        language="typescript",
        framework="node",
        description="Node.js TypeScript application.",
        files=[
            TemplateFile(path="package.json"),
            TemplateFile(path="tsconfig.json"),
            TemplateFile(path="src/index.ts"),
            TemplateFile(path="src/server.ts"),
            TemplateFile(path="tests/server.test.ts", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
            TemplateFile(path=".env.example", required=False),
        ],
        build_command="npx tsc",
        test_command="npm test",
        run_command="npx ts-node src/server.ts",
        lint_command="npx eslint .",
        tags=["application", "node", "typescript"],
        recommended_tools=["eslint", "jest", "typescript", "ts-node"],
    )
