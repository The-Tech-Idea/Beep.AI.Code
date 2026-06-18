from __future__ import annotations

import ast
from pathlib import Path


API_DIR = Path(__file__).resolve().parent.parent / "beep" / "api"


def _py_files_in(dir_path: Path) -> list[Path]:
    return sorted(p for p in dir_path.rglob("*.py") if p.name != "__init__.py")


def _string_literals_in(file_path: Path) -> list[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    strings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
    return strings


def test_no_legacy_middleware_paths_in_beep_api() -> None:
    """No /ai-middleware/ string literal remains in beep/api/ source files."""
    for py_file in _py_files_in(API_DIR):
        content = py_file.read_text(encoding="utf-8")
        assert "/ai-middleware/api/" not in content, (
            f"Legacy path found in {py_file.relative_to(API_DIR.parent)}"
        )


def test_all_endpoint_constants_start_with_v1() -> None:
    """Every exported endpoint constant starts with /v1/ or is a known non-v1 route."""
    from beep.api import endpoints

    known_non_v1 = frozenset({"MCP_REGISTRY", "CAPABILITY_DISCOVERY_TIMEOUT"})

    for name in dir(endpoints):
        if name.startswith("_"):
            continue
        value = getattr(endpoints, name)
        if name in known_non_v1:
            continue
        if isinstance(value, str) and value.startswith("/"):
            assert value.startswith("/v1/"), (
                f"endpoints.{name} = {value!r} does not start with /v1/"
            )


def test_client_uses_endpoint_constants() -> None:
    """Client and support modules import from beep.api.endpoints."""
    from beep.api.client_agent_bundle_support import import_agent_bundle as _ia

    import beep.api.endpoints as ep

    assert hasattr(ep, "V1_API_AGENTS_BUNDLES_IMPORT")

    from beep.publishing.server_deploy_support import SERVER_DEPLOY_ENDPOINT

    assert SERVER_DEPLOY_ENDPOINT == ep.V1_API_AGENTS_BUNDLES_IMPORT


def test_v1_chat_completions_constant_matches_usage() -> None:
    """The V1_CHAT_COMPLETIONS constant matches hardcoded references."""
    import beep.api.endpoints as ep

    assert ep.V1_CHAT_COMPLETIONS == "/v1/chat/completions"
    assert ep.V1_MODELS == "/v1/models"
    assert ep.V1_MESSAGES == "/v1/messages"
    assert ep.V1_RESPONSES == "/v1/responses"
    assert ep.V1_EMBEDDINGS == "/v1/embeddings"
    assert ep.V1_API_TOKENS_CHECK == "/v1/api/tokens/check"
