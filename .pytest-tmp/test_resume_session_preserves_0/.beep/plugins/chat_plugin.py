
from beep.plugins.registry import CommandPlugin, ContextPlugin, PluginInfo

class EchoCommandPlugin(CommandPlugin):
    info = PluginInfo(name="echo-command")

    def activate(self): ...

    def get_commands(self):
        return {"echo": "Echo plugin response"}

    async def handle_command(self, command: str, args: str):
        return f"plugin-echo:{args}"

class PromptContextPlugin(ContextPlugin):
    info = PluginInfo(name="prompt-context")

    def activate(self): ...

    def get_context(self):
        return "Follow plugin context rules."
