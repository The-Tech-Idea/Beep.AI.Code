"""Default coding standards for the agent."""

from __future__ import annotations

from beep.standards.models import CodingStandard

CLEAN_CODE_RULES = CodingStandard(
    name="clean_code",
    description="General clean code rules",
    rules=[
        "Use clear and intention-revealing names.",
        "Keep functions small and focused (do one thing).",
        "Avoid duplicated logic.",
        "Avoid large classes with unrelated responsibilities (God objects).",
        "Prefer explicit error handling over silent failures.",
        "Avoid unnecessary abstractions and indirection.",
        "Do not overengineer simple changes.",
    ],
    priority=100,
)

SOLID_RULES = CodingStandard(
    name="solid",
    description="SOLID design principles",
    rules=[
        "Single Responsibility: Each class/module should have one reason to change.",
        "Open/Closed: Open for extension, closed for modification.",
        "Liskov Substitution: Subtypes must be substitutable for their base types.",
        "Interface Segregation: Prefer many specific interfaces to one general one.",
        "Dependency Inversion: Depend on abstractions, not concretions.",
    ],
    priority=90,
)

DDD_RULES = CodingStandard(
    name="ddd",
    description="Domain-Driven Design rules",
    applies_to_project_types=["business_app", "enterprise"],
    rules=[
        "Put business rules in the domain layer.",
        "Use application services for use case orchestration.",
        "Use domain services only when logic does not naturally belong to one entity.",
        "Keep infrastructure concerns outside the domain layer.",
        "Do not inject repositories into entities.",
        "Do not put validation/business rules only in controllers.",
        "Prefer value objects for meaningful domain concepts.",
        "Use repositories only for aggregate roots.",
        "Add tests for domain behavior.",
    ],
    priority=80,
)

LAYER_ARCHITECTURE_RULES = CodingStandard(
    name="layer_architecture",
    description="Layered architecture rules",
    rules=[
        "No business logic inside controllers, UI components, or CLI commands.",
        "No direct database access inside domain objects.",
        "Domain layer must not depend on Infrastructure or Presentation layers.",
        "Application layer may depend on Domain layer.",
        "Infrastructure layer implements interfaces defined in Application/Domain.",
        "Presentation layer delegates to Application layer for business logic.",
    ],
    priority=85,
)

TESTING_RULES = CodingStandard(
    name="testing",
    description="Testing standards",
    rules=[
        "Add or update tests for new behavior.",
        "Tests should verify domain behavior, not just implementation details.",
        "Do not fake domain logic in tests.",
        "Use existing test framework conventions.",
    ],
    priority=70,
)

SIMPLICITY_RULES = CodingStandard(
    name="simplicity",
    description="Rules to prevent overengineering",
    rules=[
        "Use the simplest design that satisfies the task and fits the existing project.",
        "Do not introduce new layers, interfaces, or factories unless they solve a real design problem.",
        "Use domain services only when domain rules span multiple entities or value objects.",
        "Do not create service classes for simple CRUD or property updates.",
        "Preserve existing architecture when fixing bugs.",
    ],
    priority=110,  # High priority to prevent overengineering
)

DEFAULT_STANDARDS = [
    CLEAN_CODE_RULES,
    SOLID_RULES,
    LAYER_ARCHITECTURE_RULES,
    SIMPLICITY_RULES,
    TESTING_RULES,
    DDD_RULES,
]
