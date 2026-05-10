"""Standards selector for choosing relevant rules."""

from __future__ import annotations

from beep.standards.defaults import DEFAULT_STANDARDS, DDD_RULES
from beep.standards.models import ArchitectureProfile, CodingStandard, TaskType


class StandardsSelector:
    def select(
        self,
        language: str,
        project_type: str,
        task_type: TaskType,
        architecture_profile: ArchitectureProfile | None,
    ) -> list[CodingStandard]:
        selected: list[CodingStandard] = []
        seen_names: set[str] = set()

        def add(std: CodingStandard) -> None:
            if std.name not in seen_names:
                selected.append(std)
                seen_names.add(std.name)

        # Always include basics
        for std in DEFAULT_STANDARDS:
            add(std)

        # Language specific
        if language == "python":
            add(_PYTHON_RULES)
        elif language == "csharp":
            add(_CSHARP_RULES)
        elif language in ("javascript", "typescript"):
            add(_WEB_RULES)
        elif language == "java":
            add(_JAVA_RULES)
        elif language == "go":
            add(_GO_RULES)
        elif language == "rust":
            add(_RUST_RULES)
        elif language == "ruby":
            add(_RUBY_RULES)
        elif language == "ccpp":
            add(_CCPP_RULES)
        elif language == "php":
            add(_PHP_RULES)

        # Architecture profile: reinforce DDD rules for DDD/Clean Architecture
        if architecture_profile in {
            ArchitectureProfile.DDD,
            ArchitectureProfile.CLEAN_ARCHITECTURE,
        }:
            add(DDD_RULES)

        # Task specific
        if task_type in {TaskType.NEW_FEATURE, TaskType.REFACTOR}:
            add(_TESTING_RULES)
        elif task_type == TaskType.PROTOTYPE:
            add(_PROTOTYPE_RULES)

        return selected


_PYTHON_RULES = CodingStandard(
    name="python",
    description="Python specific standards",
    rules=[
        "Use type hints for function signatures.",
        "Prefer dataclasses or Pydantic models for structured data.",
        "Avoid global mutable state.",
        "Use dependency injection through constructors or function parameters.",
        "Follow PEP 8 naming conventions.",
    ],
    applies_to_languages=["python"],
)

_CSHARP_RULES = CodingStandard(
    name="csharp",
    description="C# specific standards",
    rules=[
        "Use explicit access modifiers (public, private, internal).",
        "Prefer readonly fields and immutable types where possible.",
        "Use async/await for I/O operations.",
        "Follow C# naming conventions (PascalCase for methods/classes, camelCase for locals).",
    ],
    applies_to_languages=["csharp"],
)

_WEB_RULES = CodingStandard(
    name="web",
    description="Web standards (JS/TS)",
    rules=[
        "Avoid any types in TypeScript.",
        "Use functional components and hooks for React.",
        "Keep components focused on rendering; delegate logic to hooks/services.",
    ],
    applies_to_languages=["javascript", "typescript"],
)

_TESTING_RULES = CodingStandard(
    name="testing_standards",
    description="General testing rules",
    rules=[
        "Add or update tests for new behavior.",
        "Tests should verify domain behavior, not just implementation details.",
        "Do not fake domain logic in tests.",
        "Use existing test framework conventions.",
    ],
)

_PROTOTYPE_RULES = CodingStandard(
    name="prototype",
    description="Prototype mode rules",
    rules=[
        "Allow simpler structure for prototypes.",
        "Avoid overengineering.",
        "Focus on working functionality over perfect architecture.",
    ],
    priority=120,
)

_JAVA_RULES = CodingStandard(
    name="java",
    description="Java specific standards",
    rules=[
        "Use final for immutable variables and method parameters where appropriate.",
        "Prefer composition over inheritance.",
        "Use interfaces for contracts; implement them in concrete classes.",
        "Follow Java naming conventions (PascalCase for classes, camelCase for methods/fields).",
        "Use Optional for nullable return types instead of returning null.",
    ],
    applies_to_languages=["java"],
)

_GO_RULES = CodingStandard(
    name="go",
    description="Go specific standards",
    rules=[
        "Use error values for error handling; do not use exceptions.",
        "Prefer interfaces with few methods; define interfaces where they are used.",
        "Use context.Context for cancellation and timeouts in I/O operations.",
        "Follow Go naming conventions: camelCase for exported, lowercase for unexported.",
        "Defer cleanup operations (close, unlock) immediately after resource acquisition.",
    ],
    applies_to_languages=["go"],
)

_RUST_RULES = CodingStandard(
    name="rust",
    description="Rust specific standards",
    rules=[
        "Use Result and Option types for error handling; avoid unwrap() in production code.",
        "Prefer borrowing over ownership transfer when possible.",
        "Use derive macros (Debug, Clone, PartialEq) for common trait implementations.",
        "Follow Rust naming conventions: snake_case for functions/variables, PascalCase for types.",
        "Use match expressions for exhaustive pattern matching over if-let chains.",
    ],
    applies_to_languages=["rust"],
)

_RUBY_RULES = CodingStandard(
    name="ruby",
    description="Ruby specific standards",
    rules=[
        "Follow Ruby idioms: use blocks, Enumerable, and symbols where appropriate.",
        "Prefer duck typing over explicit type checking.",
        "Use guard clauses to reduce nesting in methods.",
        "Follow Ruby naming conventions: snake_case for methods/variables, PascalCase for classes.",
        "Keep methods short; extract complex logic into private helper methods.",
    ],
    applies_to_languages=["ruby"],
)

_CCPP_RULES = CodingStandard(
    name="ccpp",
    description="C/C++ specific standards",
    rules=[
        "Use RAII for resource management; avoid raw new/delete.",
        "Prefer smart pointers (unique_ptr, shared_ptr) over raw pointers.",
        "Use const correctness for function parameters and return types.",
        "Follow C++ naming conventions: PascalCase for classes, camelCase for methods/functions.",
        "Use nullptr instead of NULL; use auto for type deduction where it improves readability.",
    ],
    applies_to_languages=["ccpp"],
)

_PHP_RULES = CodingStandard(
    name="php",
    description="PHP specific standards",
    rules=[
        "Use type declarations for function parameters and return types (PHP 7+).",
        "Prefer dependency injection over global state or static methods.",
        "Follow PSR-12 coding style guide.",
        "Use namespaces and follow PSR-4 autoloading conventions.",
        "Prefer strict comparison (===, !==) over loose comparison (==, !=).",
    ],
    applies_to_languages=["php"],
)
