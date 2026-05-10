FROM python:3.11-slim

LABEL org.opencontainers.image.title="Code Reviewer" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.description="Review code changes."

ENV BEEP_AGENT_BUNDLE=/opt/beep-agent/bundle/code-reviewer.beep-agent.json
WORKDIR /opt/beep-agent
COPY bundle/code-reviewer.beep-agent.json /opt/beep-agent/bundle/code-reviewer.beep-agent.json
COPY entrypoint.sh /opt/beep-agent/entrypoint.sh
RUN pip install --no-cache-dir "beep-ai-code>=__CLI_VERSION__"
ENTRYPOINT ["/opt/beep-agent/entrypoint.sh"]

