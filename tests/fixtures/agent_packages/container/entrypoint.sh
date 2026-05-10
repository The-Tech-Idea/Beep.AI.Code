#!/bin/sh
set -eu

if [ "$#" -eq 0 ]; then
  echo "Usage: docker run --rm <image> <goal>" >&2
  exit 2
fi

exec python -m beep agent run "$BEEP_AGENT_BUNDLE" "$@"

