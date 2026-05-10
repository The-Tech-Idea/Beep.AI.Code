"""C/C++ language adapter."""

from __future__ import annotations

import re
from pathlib import Path

from beep.languages._shared import deduplicate, has_tool
from beep.languages.base import LanguageAdapter, ProjectCommand


class CCppAdapter(LanguageAdapter):
    @property
    def name(self) -> str:
        return "ccpp"

    @property
    def extensions(self) -> list[str]:
        return [".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hh", ".hxx"]

    def detect(self, root_path: str) -> bool:
        root = Path(root_path)
        indicators = [
            root / "CMakeLists.txt",
            root / "Makefile",
            root / "makefile",
            root / "GNUmakefile",
            root / "configure",
            root / "configure.ac",
            root / "Meson.build",
        ]
        c_files = bool(
            list(root.rglob("*.c"))
            or list(root.rglob("*.cpp"))
            or list(root.rglob("*.cc"))
            or list(root.rglob("*.cxx"))
        )
        return any(p.exists() for p in indicators) or c_files

    def get_build_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        if (root / "CMakeLists.txt").exists():
            return [
                ProjectCommand(
                    name="cmake-build",
                    command=["cmake", "--build", "build"],
                    description="Build C/C++ project via CMake",
                )
            ]
        if (
            (root / "Makefile").exists()
            or (root / "makefile").exists()
            or (root / "GNUmakefile").exists()
        ):
            return [
                ProjectCommand(
                    name="make",
                    command=["make"],
                    description="Build C/C++ project via Make",
                )
            ]
        if (root / "Meson.build").exists():
            return [
                ProjectCommand(
                    name="meson-compile",
                    command=["ninja", "-C", "build"],
                    description="Build C/C++ project via Meson/Ninja",
                )
            ]
        return []

    def get_test_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        if (root / "CMakeLists.txt").exists():
            cmake_content = (root / "CMakeLists.txt").read_text(encoding="utf-8")
            if "CTest" in cmake_content or "enable_testing" in cmake_content:
                commands.append(
                    ProjectCommand(
                        name="ctest",
                        command=["ctest", "--output-on-failure"],
                        description="Run C/C++ tests via CTest",
                    )
                )
        if (root / "Makefile").exists() or (root / "makefile").exists():
            make_content = (root / "Makefile").read_text(encoding="utf-8", errors="replace")
            if re.search(r"^test\s*:", make_content, re.MULTILINE):
                commands.append(
                    ProjectCommand(
                        name="make-test",
                        command=["make", "test"],
                        description="Run C/C++ tests via Make",
                    )
                )
        if not commands:
            test_files = list(root.rglob("*_test.cpp")) + list(root.rglob("*_test.c"))
            test_files += list(root.rglob("test_*.cpp")) + list(root.rglob("test_*.c"))
            if test_files:
                commands.append(
                    ProjectCommand(
                        name="run-tests",
                        command=["./build/run_tests"],
                        description="Run compiled test binary",
                    )
                )
        return commands

    def get_lint_commands(self, root_path: str) -> list[ProjectCommand]:
        root = Path(root_path)
        commands: list[ProjectCommand] = []
        source_dir = _detect_source_dir(root)
        if has_tool("clang-tidy"):
            if (root / ".clang-tidy").exists():
                commands.append(
                    ProjectCommand(
                        name="clang-tidy",
                        command=[
                            "clang-tidy",
                            "--config-file=.clang-tidy",
                            f"{source_dir}/**/*.cpp",
                        ],
                        description="Run clang-tidy static analysis",
                    )
                )
        if has_tool("cppcheck"):
            commands.append(
                ProjectCommand(
                    name="cppcheck",
                    command=["cppcheck", "--enable=all", source_dir],
                    description="Run Cppcheck static analysis",
                )
            )
        if has_tool("clang-format"):
            commands.append(
                ProjectCommand(
                    name="clang-format",
                    command=["clang-format", "--dry-run", "--Werror", "-r", source_dir],
                    description="Check C/C++ code formatting",
                )
            )
        return commands

    def find_test_files(self, source_file: str, root_path: str) -> list[str]:
        root = Path(root_path)
        source_name = Path(source_file).stem
        candidates: list[str] = []
        patterns = [
            f"*{source_name}_test.cpp",
            f"*{source_name}_test.c",
            f"*test_{source_name}.cpp",
            f"*test_{source_name}.c",
            f"*{source_name}_test.cc",
            f"*{source_name}_test.cxx",
        ]
        for pattern in patterns:
            candidates.extend(str(p) for p in root.rglob(pattern))
        tests_dir = root / "tests"
        if tests_dir.is_dir():
            candidates.extend(str(p) for p in tests_dir.rglob(f"*{source_name}*"))
        test_dir = root / "test"
        if test_dir.is_dir():
            candidates.extend(str(p) for p in test_dir.rglob(f"*{source_name}*"))
        return deduplicate(candidates)

    def get_frameworks(self, root_path: str) -> list[str]:
        root = Path(root_path)
        frameworks: list[str] = []
        for src_file in root.rglob("*.cpp"):
            try:
                content = src_file.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                continue
            if "qt" in content and ("qobject" in content or "qwidget" in content):
                if "Qt" not in frameworks:
                    frameworks.append("Qt")
            if "boost" in content and ("boost::" in content):
                if "Boost" not in frameworks:
                    frameworks.append("Boost")
            if "grpc" in content and ("grpc::" in content):
                if "gRPC" not in frameworks:
                    frameworks.append("gRPC")
            if "protobuf" in content and ("google::protobuf" in content):
                if "Protobuf" not in frameworks:
                    frameworks.append("Protobuf")
        cmake = root / "CMakeLists.txt"
        if cmake.exists():
            content = cmake.read_text(encoding="utf-8").lower()
            if "find_package(qt" in content:
                if "Qt" not in frameworks:
                    frameworks.append("Qt")
            if "find_package(boost" in content:
                if "Boost" not in frameworks:
                    frameworks.append("Boost")
        return deduplicate(frameworks)

    def get_package_managers(self, root_path: str) -> list[str]:
        root = Path(root_path)
        managers: list[str] = []
        if (root / "CMakeLists.txt").exists():
            managers.append("cmake")
        if (root / "vcpkg.json").exists():
            managers.append("vcpkg")
        if (root / "conanfile.txt").exists() or (root / "conanfile.py").exists():
            managers.append("conan")
        if (root / "Meson.build").exists():
            managers.append("meson")
        return managers


def _detect_source_dir(root: Path) -> str:
    """Detect the primary source directory or fall back to root."""
    for candidate in ("src", "source", "lib", "include"):
        if (root / candidate).is_dir():
            return candidate
    c_files = list(root.rglob("*.c")) + list(root.rglob("*.cpp"))
    if c_files:
        common = _common_prefix_dir(c_files, root)
        if common:
            return common
    return "."


def _common_prefix_dir(paths: list[Path], root: Path) -> str | None:
    """Find the common directory prefix relative to root."""
    if not paths:
        return None
    parts_sets = [p.relative_to(root).parts[:-1] for p in paths]
    if not parts_sets:
        return None
    common = parts_sets[0]
    for parts in parts_sets[1:]:
        limit = min(len(common), len(parts))
        common = common[:limit]
        for i in range(limit):
            if common[i] != parts[i]:
                common = common[:i]
                break
    return str("/".join(common)) if common else None
