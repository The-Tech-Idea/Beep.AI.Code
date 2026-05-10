"""Project template plugins for all languages."""

from __future__ import annotations

from beep.templates.plugins.python.plugin import PythonTemplatePlugin
from beep.templates.plugins.csharp.plugin import CSharpTemplatePlugin
from beep.templates.plugins.javascript.plugin import JavaScriptTemplatePlugin
from beep.templates.plugins.typescript.plugin import TypeScriptTemplatePlugin
from beep.templates.plugins.java.plugin import JavaTemplatePlugin
from beep.templates.plugins.go.plugin import GoTemplatePlugin
from beep.templates.plugins.rust.plugin import RustTemplatePlugin
from beep.templates.plugins.ruby.plugin import RubyTemplatePlugin
from beep.templates.plugins.ccpp.plugin import CCppTemplatePlugin
from beep.templates.plugins.php.plugin import PHPPluginTemplatePlugin


BUILTIN_PLUGINS = [
    PythonTemplatePlugin(),
    CSharpTemplatePlugin(),
    JavaScriptTemplatePlugin(),
    TypeScriptTemplatePlugin(),
    JavaTemplatePlugin(),
    GoTemplatePlugin(),
    RustTemplatePlugin(),
    RubyTemplatePlugin(),
    CCppTemplatePlugin(),
    PHPPluginTemplatePlugin(),
]
