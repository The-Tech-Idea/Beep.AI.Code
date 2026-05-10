"""JavaScript project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_js_library_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="js-library",
        language="javascript",
        description="JavaScript library package.",
        files=[
            TemplateFile(path="package.json"),
            TemplateFile(path="src/index.js"),
            TemplateFile(path="tests/index.test.js", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="npm run build",
        test_command="npm test",
        lint_command="npx eslint .",
        tags=["library", "npm"],
        recommended_tools=["eslint", "jest"],
    )


def get_js_nodeapp_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="js-nodeapp",
        language="javascript",
        framework="node",
        description="Node.js application.",
        files=[
            TemplateFile(path="package.json"),
            TemplateFile(path="src/index.js"),
            TemplateFile(path="src/server.js"),
            TemplateFile(path="tests/server.test.js", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
            TemplateFile(path=".env.example", required=False),
        ],
        build_command="npm install",
        test_command="npm test",
        run_command="node src/server.js",
        lint_command="npx eslint .",
        tags=["application", "node", "server"],
        recommended_tools=["eslint", "jest", "express"],
    )
