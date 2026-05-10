"""Tests for project template plugin system."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.templates.models import ProjectTemplate, TemplateFile
from beep.templates.plugin import ProjectTemplatePlugin
from beep.templates.registry import ProjectTemplateRegistry
from beep.templates.validator import ProjectTemplateValidator, ValidationResult
from beep.templates.plugins.python import (
    get_python_library_template,
    get_python_cli_template,
    get_python_webapp_template,
)
from beep.templates.plugins.csharp import (
    get_csharp_library_template,
    get_csharp_webapi_template,
)
from beep.templates.plugins.javascript import (
    get_js_library_template,
    get_js_nodeapp_template,
)
from beep.templates.plugins.typescript import (
    get_ts_library_template,
    get_ts_nodeapp_template,
)
from beep.templates.plugins.java import (
    get_java_maven_library_template,
    get_java_springboot_template,
)
from beep.templates.plugins.go import (
    get_go_cli_template,
    get_go_webapi_template,
)
from beep.templates.plugins.rust import (
    get_rust_library_template,
    get_rust_cli_template,
)
from beep.templates.plugins.ruby import get_ruby_gem_template
from beep.templates.plugins.ccpp import get_ccpp_cmake_library_template
from beep.templates.plugins.php import (
    get_php_library_template,
    get_php_laravel_template,
)
from beep.templates.plugins import BUILTIN_PLUGINS


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestModels:
    def test_template_file_resolve_path(self):
        f = TemplateFile(path="src/{{name}}/__init__.py")
        # project_root is the project directory itself
        assert f.resolve_path("/tmp/mylib", "mylib") == str(
            Path("/tmp/mylib/src/mylib/__init__.py")
        )

    def test_template_file_resolve_content(self):
        f = TemplateFile(path="pyproject.toml", content='name = "{{name}}"')
        assert f.resolve_content("mylib") == 'name = "mylib"'

    def test_project_template_full_name(self):
        t = ProjectTemplate(name="lib", language="python", framework="fastapi")
        assert t.full_name == "python/fastapi"

    def test_project_template_full_name_no_framework(self):
        t = ProjectTemplate(name="lib", language="python")
        assert t.full_name == "python"

    def test_to_prompt_section(self):
        t = ProjectTemplate(
            name="lib",
            language="python",
            description="Test lib",
            build_command="pip install -e .",
            test_command="pytest",
            tags=["library"],
        )
        section = t.to_prompt_section()
        assert "python" in section
        assert "Test lib" in section
        assert "pytest" in section
        assert "library" in section


class TestRegistry:
    def test_register_and_get_templates(self):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)
        templates = registry.get_templates()
        assert len(templates) > 0

    def test_get_templates_by_language(self):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)
        python = registry.get_templates(language="python")
        assert all(t.language == "python" for t in python)
        assert len(python) >= 3

    def test_get_templates_by_framework(self):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)
        spring = registry.get_templates(framework="spring-boot")
        assert all(t.framework == "spring-boot" for t in spring)

    def test_get_template_by_name(self):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)
        t = registry.get_template("python-library")
        assert t is not None
        assert t.name == "python-library"

    def test_list_languages(self):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)
        langs = registry.list_languages()
        assert "python" in langs
        assert "csharp" in langs
        assert "javascript" in langs
        assert "typescript" in langs
        assert "java" in langs
        assert "go" in langs
        assert "rust" in langs
        assert "ruby" in langs
        assert "ccpp" in langs
        assert "php" in langs

    def test_list_frameworks(self):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)
        fw = registry.list_frameworks("python")
        assert "fastapi" in fw
        assert "cli" in fw


class TestValidator:
    def test_validate_matching_project(self, tmp_dir):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)

        # Create a matching Python library project
        (tmp_dir / "pyproject.toml").write_text("[project]\nname = 'mylib'")
        (tmp_dir / "src" / "mylib" / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
        (tmp_dir / "src" / "mylib" / "__init__.py").write_text("")
        (tmp_dir / "tests" / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
        (tmp_dir / "tests" / "__init__.py").write_text("")
        (tmp_dir / "tests" / "test_main.py").write_text("")
        (tmp_dir / "README.md").write_text("")

        validator = ProjectTemplateValidator(registry)
        results = validator.validate(str(tmp_dir))
        assert len(results) > 0
        # Best result should be Python library
        assert results[0].template.language == "python"

    def test_validate_non_matching_project(self, tmp_dir):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)

        (tmp_dir / "random.txt").write_text("hello")

        validator = ProjectTemplateValidator(registry)
        results = validator.validate(str(tmp_dir))
        # Should have low-scoring results
        for r in results:
            assert r.score < 1.0

    def test_get_best_template(self, tmp_dir):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)

        (tmp_dir / "go.mod").write_text("module myapp")
        (tmp_dir / "main.go").write_text("package main")

        validator = ProjectTemplateValidator(registry)
        best = validator.get_best_template(str(tmp_dir))
        assert best is not None
        assert best.template.language == "go"


class TestAllTemplates:
    """Verify every builtin template has required fields."""

    def test_python_templates(self):
        for t in [
            get_python_library_template(),
            get_python_cli_template(),
            get_python_webapp_template(),
        ]:
            assert t.name
            assert t.language == "python"
            assert t.description
            assert len(t.files) > 0

    def test_csharp_templates(self):
        for t in [get_csharp_library_template(), get_csharp_webapi_template()]:
            assert t.name
            assert t.language == "csharp"
            assert t.description
            assert len(t.files) > 0

    def test_javascript_templates(self):
        for t in [get_js_library_template(), get_js_nodeapp_template()]:
            assert t.name
            assert t.language == "javascript"
            assert t.description
            assert len(t.files) > 0

    def test_typescript_templates(self):
        for t in [get_ts_library_template(), get_ts_nodeapp_template()]:
            assert t.name
            assert t.language == "typescript"
            assert t.description
            assert len(t.files) > 0

    def test_java_templates(self):
        for t in [get_java_maven_library_template(), get_java_springboot_template()]:
            assert t.name
            assert t.language == "java"
            assert t.description
            assert len(t.files) > 0

    def test_go_templates(self):
        for t in [get_go_cli_template(), get_go_webapi_template()]:
            assert t.name
            assert t.language == "go"
            assert t.description
            assert len(t.files) > 0

    def test_rust_templates(self):
        for t in [get_rust_library_template(), get_rust_cli_template()]:
            assert t.name
            assert t.language == "rust"
            assert t.description
            assert len(t.files) > 0

    def test_ruby_templates(self):
        t = get_ruby_gem_template()
        assert t.name
        assert t.language == "ruby"
        assert t.description
        assert len(t.files) > 0

    def test_ccpp_templates(self):
        t = get_ccpp_cmake_library_template()
        assert t.name
        assert t.language == "ccpp"
        assert t.description
        assert len(t.files) > 0

    def test_php_templates(self):
        for t in [get_php_library_template(), get_php_laravel_template()]:
            assert t.name
            assert t.language == "php"
            assert t.description
            assert len(t.files) > 0


class TestBuiltinPlugins:
    def test_all_plugins_registered(self):
        registry = ProjectTemplateRegistry()
        for plugin in BUILTIN_PLUGINS:
            registry.register(plugin)
        langs = registry.list_languages()
        assert len(langs) >= 10

    def test_all_plugins_have_unique_names(self):
        names = [p.name for p in BUILTIN_PLUGINS]
        assert len(names) == len(set(names))


class TestCodeSnippetTools:
    """Test code snippet template tools."""

    def test_list_snippets(self):
        from beep.agent.tools.code_snippets import CodeSnippetListTool
        import asyncio

        tool = CodeSnippetListTool()
        assert tool.name == "code_snippet_list"
        assert tool.read_only_safe is True

        result = asyncio.run(tool.execute())
        assert result.success
        assert "fastapi-route" in result.output or "Available" in result.output

    def test_list_snippets_by_category(self):
        from beep.agent.tools.code_snippets import CodeSnippetListTool
        import asyncio

        tool = CodeSnippetListTool()
        result = asyncio.run(tool.execute(category="python"))
        assert result.success

    def test_generate_snippet(self, tmp_dir):
        from beep.agent.tools.code_snippets import CodeSnippetTool
        import asyncio

        tool = CodeSnippetTool()
        assert tool.name == "code_snippet"
        assert tool.read_only_safe is False

        output_path = str(tmp_dir / "test_route.py")
        result = asyncio.run(
            tool.execute(
                template_name="fastapi-route",
                output_path=output_path,
                variables={"route_name": "Hello", "path": "hello"},
            )
        )
        assert result.success
        assert "fastapi-route" in result.output
        assert (tmp_dir / "test_route.py").exists()

    def test_generate_snippet_missing_vars(self, tmp_dir):
        from beep.agent.tools.code_snippets import CodeSnippetTool
        import asyncio

        tool = CodeSnippetTool()
        output_path = str(tmp_dir / "test.py")
        result = asyncio.run(
            tool.execute(
                template_name="fastapi-route",
                output_path=output_path,
            )
        )
        assert not result.success
        assert "Missing variables" in result.error

    def test_generate_snippet_unknown_template(self, tmp_dir):
        from beep.agent.tools.code_snippets import CodeSnippetTool
        import asyncio

        tool = CodeSnippetTool()
        output_path = str(tmp_dir / "test.py")
        result = asyncio.run(
            tool.execute(
                template_name="nonexistent",
                output_path=output_path,
                variables={"foo": "bar"},
            )
        )
        assert not result.success
        assert "not found" in result.error
