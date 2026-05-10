"""PHP project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_php_library_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="php-library",
        language="php",
        description="PHP library package.",
        files=[
            TemplateFile(path="composer.json"),
            TemplateFile(path="src/{{name}}.php"),
            TemplateFile(path="tests/{{name}}Test.php", required=False),
            TemplateFile(path="phpunit.xml.dist", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="composer install",
        test_command="vendor/bin/phpunit",
        lint_command="vendor/bin/phpstan analyse src",
        tags=["library", "composer"],
        recommended_tools=["phpstan", "phpunit"],
    )


def get_php_laravel_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="php-laravel",
        language="php",
        framework="laravel",
        description="Laravel web application.",
        files=[
            TemplateFile(path="composer.json"),
            TemplateFile(path="artisan"),
            TemplateFile(path="routes/web.php"),
            TemplateFile(path="app/Http/Controllers/Controller.php"),
            TemplateFile(path="tests/Feature/ExampleTest.php", required=False),
            TemplateFile(path="phpunit.xml"),
            TemplateFile(path=".env.example"),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="composer install",
        test_command="php artisan test",
        run_command="php artisan serve",
        lint_command="vendor/bin/phpstan analyse",
        tags=["web", "laravel", "framework"],
        recommended_tools=["phpstan", "phpunit", "laravel"],
    )
