"""Beep.AI.Server deployment planning for portable agent bundles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from beep.agent.bundle_contract import PortableAgentBundleManifest
from beep.publishing.release_metadata import build_distribution_name, build_shared_release_metadata

SERVER_DEPLOY_ENDPOINT = "/ai-middleware/api/agents/bundles/import"
_SERVER_RUNNER_KINDS = frozenset({"beep.ai.server", "enterprise_server", "server"})


@dataclass(frozen=True)
class ServerDeploymentPlan:
    server_url: str
    endpoint_path: str
    bundle_reference: str
    agent_id: str
    overwrite: bool
    declared_runner_kinds: tuple[str, ...]
    expected_execution_target: str
    shared_release_metadata: dict[str, object]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["declared_runner_kinds"] = list(self.declared_runner_kinds)
        payload["warnings"] = list(self.warnings)
        return payload


def build_server_deployment_plan(
    manifest: PortableAgentBundleManifest,
    *,
    server_url: str,
    bundle_reference: str,
    overwrite: bool = False,
) -> ServerDeploymentPlan:
    warnings: list[str] = []
    bundle_file = Path(str(bundle_reference)).name or f"{manifest.agent_id}.beep-agent.json"
    shared_release_metadata = build_shared_release_metadata(
        manifest,
        distribution_name=build_distribution_name(manifest.agent_id),
        bundle_file=bundle_file,
        description=(manifest.description.strip() or manifest.name.strip()),
    ).to_dict()
    runner_kinds = tuple(manifest.runtime.supported_runner_kinds)
    if any(kind in _SERVER_RUNNER_KINDS for kind in runner_kinds):
        expected_execution_target = "enterprise_server"
    else:
        expected_execution_target = "local_pc"
        warnings.append(
            "Bundle does not declare a Beep.AI.Server runner kind; server import is expected to keep execution_target as local_pc."
        )
    if not manifest.compatibility.server_contract_versions:
        warnings.append(
            "Bundle does not declare compatibility.server_contract_versions; the server will treat schema_version=1 as legacy-compatible."
        )
    return ServerDeploymentPlan(
        server_url=str(server_url).rstrip("/"),
        endpoint_path=SERVER_DEPLOY_ENDPOINT,
        bundle_reference=str(bundle_reference),
        agent_id=manifest.agent_id,
        overwrite=overwrite,
        declared_runner_kinds=runner_kinds,
        expected_execution_target=expected_execution_target,
        shared_release_metadata=shared_release_metadata,
        warnings=tuple(warnings),
    )