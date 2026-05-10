# beep-agent-code-reviewer container

Review code changes.

This directory is a dry-run container wrapper for a portable Beep.AI agent bundle. It installs the CLI runtime, copies the canonical bundle, and forwards container arguments to `beep agent run`. Shared provenance and compatibility metadata is recorded in `release-metadata.json`.

## Usage

```bash
docker build -t beep-agent-code-reviewer:1.0.0 .
docker run --rm beep-agent-code-reviewer:1.0.0 inspect this repo
```

