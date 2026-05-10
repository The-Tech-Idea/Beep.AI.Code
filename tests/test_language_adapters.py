"""Tests for language adapters."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from beep.languages.registry import LanguageRegistry
from beep.languages.base import ProjectProfile
from beep.languages.java import JavaAdapter
from beep.languages.go import GoAdapter
from beep.languages.rust import RustAdapter
from beep.languages.ruby import RubyAdapter
from beep.languages.ccpp import CCppAdapter
from beep.languages.php import PHPAdapter
from beep.languages.python import PythonAdapter
from beep.languages.csharp import CSharpAdapter
from beep.languages.javascript import JavaScriptAdapter
from beep.languages.typescript import TypeScriptAdapter


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestJavaAdapter:
    def test_detect_maven(self, tmp_dir):
        (tmp_dir / "pom.xml").write_text("<project></project>")
        adapter = JavaAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_gradle(self, tmp_dir):
        (tmp_dir / "build.gradle").write_text("plugins {}")
        adapter = JavaAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_java_files(self, tmp_dir):
        (tmp_dir / "src").mkdir()
        (tmp_dir / "src" / "Main.java").write_text("class Main {}")
        adapter = JavaAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = JavaAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_build_commands_maven(self, tmp_dir):
        (tmp_dir / "pom.xml").write_text("<project></project>")
        adapter = JavaAdapter()
        cmds = adapter.get_build_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "maven-compile"

    def test_build_commands_gradle(self, tmp_dir):
        (tmp_dir / "build.gradle").write_text("plugins {}")
        adapter = JavaAdapter()
        cmds = adapter.get_build_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "gradle-build"

    def test_test_commands(self, tmp_dir):
        (tmp_dir / "pom.xml").write_text("<project></project>")
        adapter = JavaAdapter()
        cmds = adapter.get_test_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "maven-test"

    def test_frameworks_spring(self, tmp_dir):
        pom = """<project><dependencies>
            <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot</artifactId></dependency>
        </dependencies></project>"""
        (tmp_dir / "pom.xml").write_text(pom)
        adapter = JavaAdapter()
        frameworks = adapter.get_frameworks(str(tmp_dir))
        assert "Spring Boot" in frameworks

    def test_package_managers(self, tmp_dir):
        (tmp_dir / "pom.xml").write_text("<project></project>")
        adapter = JavaAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "maven" in managers

    def test_name_and_extensions(self):
        adapter = JavaAdapter()
        assert adapter.name == "java"
        assert ".java" in adapter.extensions


class TestGoAdapter:
    def test_detect_go_mod(self, tmp_dir):
        (tmp_dir / "go.mod").write_text("module example")
        adapter = GoAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_go_files(self, tmp_dir):
        (tmp_dir / "main.go").write_text("package main")
        adapter = GoAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = GoAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_build_commands(self, tmp_dir):
        (tmp_dir / "go.mod").write_text("module example")
        adapter = GoAdapter()
        cmds = adapter.get_build_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "go-build"

    def test_test_commands(self, tmp_dir):
        adapter = GoAdapter()
        cmds = adapter.get_test_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "go-test"

    def test_find_test_files(self, tmp_dir):
        (tmp_dir / "utils.go").write_text("package utils")
        (tmp_dir / "utils_test.go").write_text("package utils")
        adapter = GoAdapter()
        test_files = adapter.find_test_files(str(tmp_dir / "utils.go"), str(tmp_dir))
        assert len(test_files) == 1
        assert test_files[0].endswith("utils_test.go")

    def test_package_managers(self, tmp_dir):
        (tmp_dir / "go.mod").write_text("module example")
        adapter = GoAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "go-modules" in managers


class TestRustAdapter:
    def test_detect_cargo_toml(self, tmp_dir):
        (tmp_dir / "Cargo.toml").write_text('[package]\nname = "test"')
        adapter = RustAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_rs_files(self, tmp_dir):
        (tmp_dir / "main.rs").write_text("fn main() {}")
        adapter = RustAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = RustAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_build_commands(self, tmp_dir):
        (tmp_dir / "Cargo.toml").write_text('[package]\nname = "test"')
        adapter = RustAdapter()
        cmds = adapter.get_build_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "cargo-build"

    def test_test_commands(self, tmp_dir):
        adapter = RustAdapter()
        cmds = adapter.get_test_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "cargo-test"

    def test_lint_commands(self, tmp_dir):
        adapter = RustAdapter()
        cmds = adapter.get_lint_commands(str(tmp_dir))
        assert any(c.name == "cargo-clippy" for c in cmds)
        assert any(c.name == "cargo-fmt" for c in cmds)

    def test_frameworks_tokio(self, tmp_dir):
        cargo = '[dependencies]\ntokio = "1.0"'
        (tmp_dir / "Cargo.toml").write_text(cargo)
        adapter = RustAdapter()
        frameworks = adapter.get_frameworks(str(tmp_dir))
        assert "Tokio" in frameworks

    def test_package_managers(self, tmp_dir):
        (tmp_dir / "Cargo.toml").write_text('[package]\nname = "test"')
        adapter = RustAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "cargo" in managers


class TestRubyAdapter:
    def test_detect_gemfile(self, tmp_dir):
        (tmp_dir / "Gemfile").write_text("source 'https://rubygems.org'")
        adapter = RubyAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_ruby_files(self, tmp_dir):
        (tmp_dir / "app.rb").write_text("puts 'hello'")
        adapter = RubyAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = RubyAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_test_commands_rspec(self, tmp_dir):
        (tmp_dir / "Gemfile").write_text("gem 'rspec'")
        adapter = RubyAdapter()
        cmds = adapter.get_test_commands(str(tmp_dir))
        assert any(c.name == "rspec" for c in cmds)

    def test_lint_commands_rubocop(self, tmp_dir):
        (tmp_dir / "Gemfile").write_text("gem 'rubocop'")
        adapter = RubyAdapter()
        cmds = adapter.get_lint_commands(str(tmp_dir))
        assert any(c.name == "rubocop" for c in cmds)

    def test_frameworks_rails(self, tmp_dir):
        (tmp_dir / "Gemfile").write_text("gem 'rails'")
        adapter = RubyAdapter()
        frameworks = adapter.get_frameworks(str(tmp_dir))
        assert "Ruby on Rails" in frameworks

    def test_package_managers(self, tmp_dir):
        (tmp_dir / "Gemfile").write_text("source 'https://rubygems.org'")
        adapter = RubyAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "bundler" in managers


class TestCCppAdapter:
    def test_detect_cmake(self, tmp_dir):
        (tmp_dir / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")
        adapter = CCppAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_makefile(self, tmp_dir):
        (tmp_dir / "Makefile").write_text("all:\n\tgcc main.c")
        adapter = CCppAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_c_files(self, tmp_dir):
        (tmp_dir / "main.c").write_text("int main() { return 0; }")
        adapter = CCppAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = CCppAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_build_commands_cmake(self, tmp_dir):
        (tmp_dir / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")
        adapter = CCppAdapter()
        cmds = adapter.get_build_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "cmake-build"

    def test_build_commands_make(self, tmp_dir):
        (tmp_dir / "Makefile").write_text("all:\n\tgcc main.c")
        adapter = CCppAdapter()
        cmds = adapter.get_build_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "make"

    def test_package_managers_vcpkg(self, tmp_dir):
        (tmp_dir / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")
        (tmp_dir / "vcpkg.json").write_text("{}")
        adapter = CCppAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "cmake" in managers
        assert "vcpkg" in managers


class TestPHPAdapter:
    def test_detect_composer(self, tmp_dir):
        (tmp_dir / "composer.json").write_text('{"name": "test/project"}')
        adapter = PHPAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_php_files(self, tmp_dir):
        (tmp_dir / "index.php").write_text("<?php echo 'hello';")
        adapter = PHPAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = PHPAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_test_commands_phpunit(self, tmp_dir):
        composer = '{"require-dev": {"phpunit/phpunit": "^9.0"}}'
        (tmp_dir / "composer.json").write_text(composer)
        adapter = PHPAdapter()
        cmds = adapter.get_test_commands(str(tmp_dir))
        assert any(c.name == "phpunit" for c in cmds)

    def test_test_commands_artisan(self, tmp_dir):
        (tmp_dir / "artisan").write_text("#!/usr/bin/env php")
        adapter = PHPAdapter()
        cmds = adapter.get_test_commands(str(tmp_dir))
        assert any(c.name == "artisan-test" for c in cmds)

    def test_lint_commands_phpstan(self, tmp_dir):
        composer = '{"require-dev": {"phpstan/phpstan": "^1.0"}}'
        (tmp_dir / "composer.json").write_text(composer)
        adapter = PHPAdapter()
        cmds = adapter.get_lint_commands(str(tmp_dir))
        assert any(c.name == "phpstan" for c in cmds)

    def test_frameworks_laravel(self, tmp_dir):
        composer = '{"require": {"laravel/framework": "^10.0"}}'
        (tmp_dir / "composer.json").write_text(composer)
        adapter = PHPAdapter()
        frameworks = adapter.get_frameworks(str(tmp_dir))
        assert "Laravel" in frameworks

    def test_package_managers(self, tmp_dir):
        (tmp_dir / "composer.json").write_text('{"name": "test/project"}')
        adapter = PHPAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "composer" in managers


class TestLanguageRegistry:
    def test_default_adapters_count(self):
        registry = LanguageRegistry()
        assert len(registry._adapters) == 10

    def test_detect_python(self, tmp_dir):
        (tmp_dir / "main.py").write_text("print('hello')")
        registry = LanguageRegistry()
        langs = registry.detect_languages(str(tmp_dir))
        assert any(a.name == "python" for a in langs)

    def test_detect_java(self, tmp_dir):
        (tmp_dir / "pom.xml").write_text("<project></project>")
        registry = LanguageRegistry()
        langs = registry.detect_languages(str(tmp_dir))
        assert any(a.name == "java" for a in langs)

    def test_detect_go(self, tmp_dir):
        (tmp_dir / "go.mod").write_text("module example")
        registry = LanguageRegistry()
        langs = registry.detect_languages(str(tmp_dir))
        assert any(a.name == "go" for a in langs)

    def test_detect_rust(self, tmp_dir):
        (tmp_dir / "Cargo.toml").write_text('[package]\nname = "test"')
        registry = LanguageRegistry()
        langs = registry.detect_languages(str(tmp_dir))
        assert any(a.name == "rust" for a in langs)

    def test_detect_ruby(self, tmp_dir):
        (tmp_dir / "Gemfile").write_text("source 'https://rubygems.org'")
        registry = LanguageRegistry()
        langs = registry.detect_languages(str(tmp_dir))
        assert any(a.name == "ruby" for a in langs)

    def test_detect_ccpp(self, tmp_dir):
        (tmp_dir / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")
        registry = LanguageRegistry()
        langs = registry.detect_languages(str(tmp_dir))
        assert any(a.name == "ccpp" for a in langs)

    def test_detect_php(self, tmp_dir):
        (tmp_dir / "composer.json").write_text('{"name": "test/project"}')
        registry = LanguageRegistry()
        langs = registry.detect_languages(str(tmp_dir))
        assert any(a.name == "php" for a in langs)

    def test_build_profile(self, tmp_dir):
        (tmp_dir / "go.mod").write_text("module example")
        (tmp_dir / "main.go").write_text("package main\nfunc main() {}")
        registry = LanguageRegistry()
        profile = registry.build_profile(str(tmp_dir))
        assert "go" in profile.languages
        assert len(profile.build_commands) > 0
        assert len(profile.test_commands) > 0

    def test_get_adapter(self):
        registry = LanguageRegistry()
        adapter = registry.get_adapter("python")
        assert adapter is not None
        assert adapter.name == "python"

    def test_get_adapter_missing(self):
        registry = LanguageRegistry()
        adapter = registry.get_adapter("nonexistent")
        assert adapter is None


class TestPythonAdapter:
    def test_detect_pyproject(self, tmp_dir):
        (tmp_dir / "pyproject.toml").write_text("[project]\nname = 'test'")
        adapter = PythonAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_requirements(self, tmp_dir):
        (tmp_dir / "requirements.txt").write_text("flask")
        adapter = PythonAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_python_files(self, tmp_dir):
        (tmp_dir / "main.py").write_text("print('hello')")
        adapter = PythonAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = PythonAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_build_commands(self, tmp_dir):
        adapter = PythonAdapter()
        assert adapter.get_build_commands(str(tmp_dir)) == []

    def test_test_commands(self, tmp_dir):
        adapter = PythonAdapter()
        cmds = adapter.get_test_commands(str(tmp_dir))
        assert len(cmds) == 1

    def test_lint_commands(self, tmp_dir):
        adapter = PythonAdapter()
        cmds = adapter.get_lint_commands(str(tmp_dir))
        assert isinstance(cmds, list)

    def test_frameworks_django(self, tmp_dir):
        (tmp_dir / "manage.py").write_text("#!/usr/bin/env python")
        adapter = PythonAdapter()
        frameworks = adapter.get_frameworks(str(tmp_dir))
        assert "Django" in frameworks

    def test_package_managers(self, tmp_dir):
        (tmp_dir / "pyproject.toml").write_text("[project]\nname = 'test'")
        adapter = PythonAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "pip" in managers

    def test_name_and_extensions(self):
        adapter = PythonAdapter()
        assert adapter.name == "python"
        assert ".py" in adapter.extensions


class TestCSharpAdapter:
    def test_detect_sln(self, tmp_dir):
        (tmp_dir / "MyApp.sln").write_text("Microsoft Visual Studio Solution File")
        adapter = CSharpAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_csproj(self, tmp_dir):
        (tmp_dir / "MyApp.csproj").write_text("<Project>")
        adapter = CSharpAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = CSharpAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_build_commands(self, tmp_dir):
        adapter = CSharpAdapter()
        cmds = adapter.get_build_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "dotnet-build"

    def test_test_commands(self, tmp_dir):
        adapter = CSharpAdapter()
        cmds = adapter.get_test_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "dotnet-test"

    def test_lint_commands(self, tmp_dir):
        adapter = CSharpAdapter()
        cmds = adapter.get_lint_commands(str(tmp_dir))
        assert len(cmds) == 1
        assert cmds[0].name == "dotnet-format"

    def test_package_managers(self, tmp_dir):
        (tmp_dir / "MyApp.csproj").write_text("<Project>")
        adapter = CSharpAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "dotnet" in managers

    def test_name_and_extensions(self):
        adapter = CSharpAdapter()
        assert adapter.name == "csharp"
        assert ".cs" in adapter.extensions


class TestJavaScriptAdapter:
    def test_detect_package_json(self, tmp_dir):
        (tmp_dir / "package.json").write_text('{"name": "test"}')
        (tmp_dir / "index.js").write_text("console.log('hi')")
        adapter = JavaScriptAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_detect_js_only(self, tmp_dir):
        (tmp_dir / "index.js").write_text("console.log('hi')")
        adapter = JavaScriptAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect_ts_only(self, tmp_dir):
        (tmp_dir / "tsconfig.json").write_text("{}")
        (tmp_dir / "index.js").write_text("console.log('hi')")
        adapter = JavaScriptAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = JavaScriptAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_build_commands_no_pkg(self, tmp_dir):
        adapter = JavaScriptAdapter()
        assert adapter.get_build_commands(str(tmp_dir)) == []

    def test_test_commands_no_pkg(self, tmp_dir):
        adapter = JavaScriptAdapter()
        assert adapter.get_test_commands(str(tmp_dir)) == []

    def test_package_managers(self, tmp_dir):
        (tmp_dir / "yarn.lock").write_text("")
        adapter = JavaScriptAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "yarn" in managers

    def test_name_and_extensions(self):
        adapter = JavaScriptAdapter()
        assert adapter.name == "javascript"
        assert ".js" in adapter.extensions


class TestTypeScriptAdapter:
    def test_detect_tsconfig(self, tmp_dir):
        (tmp_dir / "tsconfig.json").write_text("{}")
        (tmp_dir / "index.ts").write_text("console.log('hi')")
        adapter = TypeScriptAdapter()
        assert adapter.detect(str(tmp_dir))

    def test_no_detect(self, tmp_dir):
        adapter = TypeScriptAdapter()
        assert not adapter.detect(str(tmp_dir))

    def test_build_commands(self, tmp_dir):
        (tmp_dir / "tsconfig.json").write_text("{}")
        adapter = TypeScriptAdapter()
        cmds = adapter.get_build_commands(str(tmp_dir))
        assert len(cmds) >= 1
        assert cmds[0].name == "tsc"

    def test_test_commands_no_pkg(self, tmp_dir):
        adapter = TypeScriptAdapter()
        assert adapter.get_test_commands(str(tmp_dir)) == []

    def test_package_managers(self, tmp_dir):
        (tmp_dir / "tsconfig.json").write_text("{}")
        (tmp_dir / "pnpm-lock.yaml").write_text("")
        adapter = TypeScriptAdapter()
        managers = adapter.get_package_managers(str(tmp_dir))
        assert "pnpm" in managers

    def test_name_and_extensions(self):
        adapter = TypeScriptAdapter()
        assert adapter.name == "typescript"
        assert ".ts" in adapter.extensions
