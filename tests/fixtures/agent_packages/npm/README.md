# beep-agent-code-reviewer

Review code changes.

This package is a local wrapper around a Phase 17 portable Beep.AI agent bundle. It exposes the bundled manifest for inspection and later publish/deployment adapters. The shared release metadata is written to `release-metadata.json`.

## Included Files

- `bundle/code-reviewer.beep-agent.json`
- `release-metadata.json`
- `index.cjs`

## Usage

```javascript
const agentBundle = require("beep-agent-code-reviewer");

const manifest = agentBundle.loadBundle();
console.log(manifest.agent_id, manifest.bundle_version);
```
