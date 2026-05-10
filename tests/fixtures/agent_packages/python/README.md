# beep-agent-code-reviewer

Review code changes.

This package is a local Python wrapper around a Phase 17 portable Beep.AI agent bundle. It keeps the bundle payload available to build and publish tooling without redefining agent semantics. The shared release metadata is written to `release-metadata.json`.

## Usage

```python
from beep_agent_code_reviewer import bundle_path, load_manifest

manifest = load_manifest()
print(manifest["agent_id"], manifest["bundle_version"])

with bundle_path() as path:
    print(path)
```
