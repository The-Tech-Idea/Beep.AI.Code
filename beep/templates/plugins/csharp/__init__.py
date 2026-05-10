"""C# project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_csharp_library_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="csharp-library",
        language="csharp",
        description="Standard C# class library.",
        files=[
            TemplateFile(path="{{name}}.sln"),
            TemplateFile(path="{{name}}/{{name}}.csproj"),
            TemplateFile(path="{{name}}/Class1.cs", required=False),
            TemplateFile(path="tests/Tests.csproj"),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="dotnet build",
        test_command="dotnet test",
        lint_command="dotnet format --verify-no-changes",
        tags=["library", "dotnet"],
        recommended_tools=["dotnet"],
    )


def get_csharp_webapi_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="csharp-webapi",
        language="csharp",
        framework="aspnetcore",
        description="ASP.NET Core Web API project.",
        files=[
            TemplateFile(path="{{name}}.sln"),
            TemplateFile(path="src/{{name}}/{{name}}.csproj"),
            TemplateFile(path="src/{{name}}/Program.cs"),
            TemplateFile(path="src/{{name}}/appsettings.json"),
            TemplateFile(path="tests/Tests.csproj"),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="dotnet build",
        test_command="dotnet test",
        run_command="dotnet run --project src/{{name}}",
        lint_command="dotnet format --verify-no-changes",
        tags=["web", "api", "aspnetcore"],
        recommended_tools=["dotnet"],
    )
