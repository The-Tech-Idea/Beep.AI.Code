"""Registry for language adapters with automatic detection."""

from __future__ import annotations

from beep.languages.base import LanguageAdapter, ProjectProfile


class LanguageRegistry:
    """Manages language adapters and detects project languages."""

    def __init__(self, adapters: list[LanguageAdapter] | None = None) -> None:
        self._adapters = adapters or self._default_adapters()

    def register(self, adapter: LanguageAdapter) -> None:
        self._adapters.append(adapter)

    def detect_languages(self, root_path: str) -> list[LanguageAdapter]:
        return [a for a in self._adapters if a.detect(root_path)]

    def get_adapter(self, name: str) -> LanguageAdapter | None:
        for adapter in self._adapters:
            if adapter.name == name:
                return adapter
        return None

    def build_profile(self, root_path: str) -> ProjectProfile:
        detected = self.detect_languages(root_path)
        profile = ProjectProfile()
        for adapter in detected:
            profile.languages.append(adapter.name)
            profile.build_commands.extend(adapter.get_build_commands(root_path))
            profile.test_commands.extend(adapter.get_test_commands(root_path))
            profile.lint_commands.extend(adapter.get_lint_commands(root_path))
            fw = adapter.get_frameworks(root_path)
            if fw:
                profile.frameworks.extend(fw)
            pm = adapter.get_package_managers(root_path)
            if pm:
                profile.package_managers.extend(pm)
        return profile

    def find_test_files_for(self, source_file: str, root_path: str) -> list[str]:
        from pathlib import Path

        ext = Path(source_file).suffix.lower()
        for adapter in self._adapters:
            if ext in adapter.extensions and adapter.detect(root_path):
                return adapter.find_test_files(source_file, root_path)
        for adapter in self._adapters:
            if adapter.detect(root_path):
                return adapter.find_test_files(source_file, root_path)
        return []

    @staticmethod
    def _default_adapters() -> list[LanguageAdapter]:
        from beep.languages.ccpp import CCppAdapter
        from beep.languages.csharp import CSharpAdapter
        from beep.languages.go import GoAdapter
        from beep.languages.java import JavaAdapter
        from beep.languages.javascript import JavaScriptAdapter
        from beep.languages.php import PHPAdapter
        from beep.languages.python import PythonAdapter
        from beep.languages.ruby import RubyAdapter
        from beep.languages.rust import RustAdapter
        from beep.languages.typescript import TypeScriptAdapter

        return [
            PythonAdapter(),
            CSharpAdapter(),
            JavaScriptAdapter(),
            TypeScriptAdapter(),
            JavaAdapter(),
            GoAdapter(),
            RustAdapter(),
            RubyAdapter(),
            CCppAdapter(),
            PHPAdapter(),
        ]
