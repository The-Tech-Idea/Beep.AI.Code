"""Ruby language adapter."""

from __future__ import annotations

import re
from pathlib import Path

from beep.languages._shared import deduplicate
from beep.languages.base import LanguageAdapter, ProjectCommand


class RubyAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "ruby"

    @property
    def extensions(self) -> list[str]:
        return [".rb", ".rake", ".gemspec"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        indicators = [
            root / "Gemfile",
            root / "Rakefile",
            root / "config.ru",
            root / "Gemfile.lock",
        ]
        return any(p.exists() for p in indicators) or bool(list(root.rglob("*.rb")))

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        return []

    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        gemfile = root / "Gemfile"
        if gemfile.exists():
            content = gemfile.read_text(encoding="utf-8")
            if "rspec" in content.lower():
                commands.append(
                    ProjectCommand(
                        name="rspec",
                        command=["bundle", "exec", "rspec"],
                        description="Run RSpec tests",
                    )
                )
            if "minitest" in content.lower():
                commands.append(
                    ProjectCommand(
                        name="minitest",
                        command=["bundle", "exec", "rake", "test"],
                        description="Run Minitest tests",
                    )
                )
        if (root / "Rakefile").exists() and not commands:
            commands.append(
                ProjectCommand(
                    name="rake-test",
                    command=["rake", "test"],
                    description="Run tests via Rake",
                )
            )
        test_dir = root / "test"
        if test_dir.is_dir() and not commands:
            commands.append(
                ProjectCommand(
                    name="ruby-test",
                    command=[
                        "ruby",
                        "-Itest",
                        "-e",
                        'Dir.glob("test/**/*_test.rb").each { |f| require f }',
                    ],
                    description="Run Ruby test files",
                )
            )
        spec_dir = root / "spec"
        if spec_dir.is_dir() and not commands:
            commands.append(
                ProjectCommand(
                    name="rspec",
                    command=["bundle", "exec", "rspec"],
                    description="Run RSpec tests",
                )
            )
        return commands

    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        gemfile = root / "Gemfile"
        if gemfile.exists():
            content = gemfile.read_text(encoding="utf-8")
            if "rubocop" in content.lower():
                commands.append(
                    ProjectCommand(
                        name="rubocop",
                        command=["bundle", "exec", "rubocop"],
                        description="Run RuboCop linter",
                    )
                )
        if (root / ".rubocop.yml").exists() and not commands:
            commands.append(
                ProjectCommand(
                    name="rubocop",
                    command=["rubocop"],
                    description="Run RuboCop linter",
                )
            )
        return commands

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        root = Path(root_path)
        source_name = Path(source_file).stem
        candidates: list[str] = []

        test_dir = root / "test"
        if test_dir.is_dir():
            candidates.extend(str(p) for p in test_dir.rglob(f"*{source_name}*test*.rb"))
            candidates.extend(str(p) for p in test_dir.rglob(f"test_{source_name}*.rb"))

        spec_dir = root / "spec"
        if spec_dir.is_dir():
            candidates.extend(str(p) for p in spec_dir.rglob(f"*{source_name}*_spec*.rb"))
            candidates.extend(str(p) for p in spec_dir.rglob(f"{source_name}_spec.rb"))

        return deduplicate(candidates)

    def get_frameworks(self, root_path: str) -> list[str]:
        root = Path(root_path)
        frameworks: list[str] = []
        gemfile = root / "Gemfile"
        if gemfile.exists():
            content = gemfile.read_text(encoding="utf-8")
            if _gem_in_file(content, "rails"):
                frameworks.append("Ruby on Rails")
            if _gem_in_file(content, "sinatra"):
                frameworks.append("Sinatra")
            if _gem_in_file(content, "hanami"):
                frameworks.append("Hanami")
            if _gem_in_file(content, "sidekiq"):
                frameworks.append("Sidekiq")
            if _gem_in_file(content, "sequel"):
                frameworks.append("Sequel")
            if _gem_in_file(content, "rom-rb") or _gem_in_file(content, "rom"):
                frameworks.append("ROM")
        return deduplicate(frameworks)

    def get_package_managers(self, root_path: str) -> list[str]:
        root = Path(root_path)
        managers: list[str] = []
        if (root / "Gemfile").exists():
            managers.append("bundler")
        return managers


def _gem_in_file(gemfile_content: str, gem_name: str) -> bool:
    return bool(re.search(rf'["\']{gem_name}["\']|:{gem_name}\b', gemfile_content, re.IGNORECASE))
