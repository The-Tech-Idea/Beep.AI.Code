"""C/C++ project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_ccpp_cmake_library_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="ccpp-cmake",
        language="ccpp",
        description="CMake-based C/C++ library.",
        files=[
            TemplateFile(path="CMakeLists.txt"),
            TemplateFile(path="src/main.cpp"),
            TemplateFile(path="include/{{name}}.hpp", required=False),
            TemplateFile(path="tests/test_main.cpp", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="cmake --build build",
        test_command="ctest --output-on-failure",
        lint_command="clang-tidy src/*.cpp",
        tags=["library", "cmake"],
        recommended_tools=["cmake", "clang-tidy", "clang-format"],
    )
