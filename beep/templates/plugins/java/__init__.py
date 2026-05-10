"""Java project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_java_maven_library_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="java-library",
        language="java",
        description="Maven-based Java library.",
        files=[
            TemplateFile(path="pom.xml"),
            TemplateFile(path="src/main/java/com/example/{{name}}/App.java"),
            TemplateFile(path="src/test/java/com/example/{{name}}/AppTest.java", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="mvn compile",
        test_command="mvn test",
        lint_command="mvn checkstyle:check",
        tags=["library", "maven"],
        recommended_tools=["maven"],
    )


def get_java_springboot_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="java-springboot",
        language="java",
        framework="spring-boot",
        description="Spring Boot web application.",
        files=[
            TemplateFile(path="pom.xml"),
            TemplateFile(path="src/main/java/com/example/{{name}}/Application.java"),
            TemplateFile(
                path="src/main/java/com/example/{{name}}/controller/HelloController.java",
                required=False,
            ),
            TemplateFile(path="src/main/resources/application.properties"),
            TemplateFile(
                path="src/test/java/com/example/{{name}}/ApplicationTests.java", required=False
            ),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="mvn compile",
        test_command="mvn test",
        run_command="mvn spring-boot:run",
        lint_command="mvn checkstyle:check",
        tags=["web", "spring-boot"],
        recommended_tools=["maven", "spring-boot"],
    )
