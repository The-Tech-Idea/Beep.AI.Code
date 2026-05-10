"""PHP language adapter."""

from __future__ import annotations

import json
from pathlib import Path

from beep.languages._shared import deduplicate
from beep.languages.base import LanguageAdapter, ProjectCommand


class PHPAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "php"

    @property
    def extensions(self) -> list[str]:
        return [".php"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        indicators = [
            root / "composer.json",
            root / "composer.lock",
            root / "artisan",
        ]
        return any(p.exists() for p in indicators) or bool(list(root.rglob("*.php")))

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        return []

    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        composer = _read_composer_json(root)

        if composer and (
            "phpunit" in _get_all_deps(composer) or "phpunit/phpunit" in _get_all_deps(composer)
        ):
            commands.append(
                ProjectCommand(
                    name="phpunit",
                    command=["vendor/bin/phpunit"],
                    description="Run PHPUnit tests",
                )
            )
        if composer and (
            "pest" in _get_all_deps(composer) or "pestphp/pest" in _get_all_deps(composer)
        ):
            commands.append(
                ProjectCommand(
                    name="pest",
                    command=["vendor/bin/pest"],
                    description="Run Pest tests",
                )
            )

        if (root / "artisan").exists():
            commands.append(
                ProjectCommand(
                    name="artisan-test",
                    command=["php", "artisan", "test"],
                    description="Run Laravel tests via Artisan",
                )
            )

        if (root / "phpunit.xml").exists() or (root / "phpunit.xml.dist").exists():
            if not commands:
                commands.append(
                    ProjectCommand(
                        name="phpunit",
                        command=["vendor/bin/phpunit"],
                        description="Run PHPUnit tests",
                    )
                )

        return commands

    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        composer = _read_composer_json(root)
        all_deps = _get_all_deps(composer) if composer else {}

        if "phpstan" in all_deps or "phpstan/phpstan" in all_deps:
            commands.append(
                ProjectCommand(
                    name="phpstan",
                    command=["vendor/bin/phpstan", "analyse", "src"],
                    description="Run PHPStan static analysis",
                )
            )
        if "psalm" in all_deps or "vimeo/psalm" in all_deps:
            commands.append(
                ProjectCommand(
                    name="psalm",
                    command=["vendor/bin/psalm"],
                    description="Run Psalm static analysis",
                )
            )
        if "php-cs-fixer" in all_deps or "friendsofphp/php-cs-fixer" in all_deps:
            commands.append(
                ProjectCommand(
                    name="php-cs-fixer",
                    command=["vendor/bin/php-cs-fixer", "fix", "--dry-run", "--diff"],
                    description="Check PHP code style with PHP CS Fixer",
                )
            )
        if "phpcs" in all_deps or "squizlabs/php_codesniffer" in all_deps:
            commands.append(
                ProjectCommand(
                    name="phpcs",
                    command=["vendor/bin/phpcs", "src"],
                    description="Run PHP_CodeSniffer",
                )
            )

        if (root / "phpstan.neon").exists() or (root / "phpstan.neon.dist").exists():
            has_phpstan = any("phpstan" in c.shell_form for c in commands)
            if not has_phpstan:
                commands.append(
                    ProjectCommand(
                        name="phpstan",
                        command=["vendor/bin/phpstan", "analyse", "src"],
                        description="Run PHPStan static analysis",
                    )
                )

        if (root / "psalm.xml").exists() or (root / "psalm.xml.dist").exists():
            has_psalm = any("psalm" in c.shell_form for c in commands)
            if not has_psalm:
                commands.append(
                    ProjectCommand(
                        name="psalm",
                        command=["vendor/bin/psalm"],
                        description="Run Psalm static analysis",
                    )
                )

        if not commands:
            commands.append(
                ProjectCommand(
                    name="php-lint",
                    command=["php", "-l", "src/"],
                    description="Run PHP syntax check",
                )
            )

        return commands

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        root = Path(root_path)
        source_name = Path(source_file).stem
        candidates: list[str] = []

        tests_dir = root / "tests"
        if tests_dir.is_dir():
            candidates.extend(str(p) for p in tests_dir.rglob(f"*{source_name}*Test.php"))
            candidates.extend(str(p) for p in tests_dir.rglob(f"*{source_name}*test.php"))

        test_dir = root / "test"
        if test_dir.is_dir():
            candidates.extend(str(p) for p in test_dir.rglob(f"*{source_name}*"))

        return deduplicate(candidates)

    def get_frameworks(self, root_path: str) -> list[str]:
        root = Path(root_path)
        frameworks: list[str] = []
        composer = _read_composer_json(root)
        all_deps = _get_all_deps(composer) if composer else {}

        if "laravel/framework" in all_deps or "laravel" in all_deps:
            frameworks.append("Laravel")
        if "symfony/symfony" in all_deps or "symfony/" in str(all_deps):
            frameworks.append("Symfony")
        if "codeigniter4" in all_deps or "codeigniter" in all_deps:
            frameworks.append("CodeIgniter")
        if "cakephp/cakephp" in all_deps:
            frameworks.append("CakePHP")
        if "yiisoft/yii2" in all_deps:
            frameworks.append("Yii2")
        if "slim/slim" in all_deps:
            frameworks.append("Slim")

        if (root / "artisan").exists() and "Laravel" not in frameworks:
            frameworks.append("Laravel")

        return deduplicate(frameworks)

    def get_package_managers(self, root_path: str) -> list[str]:
        root = Path(root_path)
        managers: list[str] = []
        if (root / "composer.json").exists():
            managers.append("composer")
        return managers


def _read_composer_json(root: Path) -> dict | None:
    composer_path = root / "composer.json"
    if not composer_path.exists():
        return None
    try:
        return json.loads(composer_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _get_all_deps(composer: dict) -> set[str]:
    deps: set[str] = set()
    deps.update(composer.get("require", {}).keys())
    deps.update(composer.get("require-dev", {}).keys())
    return deps
