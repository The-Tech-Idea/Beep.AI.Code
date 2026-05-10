"""Ruby project templates."""

from __future__ import annotations

from beep.templates.models import ProjectTemplate, TemplateFile


def get_ruby_gem_template() -> ProjectTemplate:
    return ProjectTemplate(
        name="ruby-gem",
        language="ruby",
        description="Ruby gem library.",
        files=[
            TemplateFile(path="{{name}}.gemspec"),
            TemplateFile(path="Gemfile"),
            TemplateFile(path="lib/{{name}}.rb"),
            TemplateFile(path="lib/{{name}}/version.rb", required=False),
            TemplateFile(path="test/test_helper.rb", required=False),
            TemplateFile(path="README.md"),
            TemplateFile(path=".gitignore"),
        ],
        build_command="bundle install",
        test_command="bundle exec rake test",
        lint_command="bundle exec rubocop",
        tags=["library", "gem"],
        recommended_tools=["rubocop", "rake"],
    )
