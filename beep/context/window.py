"""Context window management.

Handles token counting, context summarization, and smart truncation
to stay within model context limits.
"""

from __future__ import annotations

from dataclasses import dataclass

TOKENS_PER_CHAR_ESTIMATE = 0.35


@dataclass
class ContextBudget:
    """Context window budget tracking."""

    max_tokens: int = 128000
    reserved_for_response: int = 4096
    system_prompt_tokens: int = 0
    message_tokens: int = 0
    context_tokens: int = 0

    @property
    def available_tokens(self) -> int:
        return (
            self.max_tokens
            - self.reserved_for_response
            - self.system_prompt_tokens
            - self.message_tokens
            - self.context_tokens
        )

    @property
    def is_over_budget(self) -> bool:
        return self.available_tokens < 0

    @property
    def usage_percent(self) -> float:
        used = (
            self.system_prompt_tokens
            + self.message_tokens
            + self.context_tokens
        )
        return used / (self.max_tokens - self.reserved_for_response)


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses a rough character-based estimate. For accurate counting,
    use the model's tokenizer.
    """
    return int(len(text) * TOKENS_PER_CHAR_ESTIMATE)


def _group_conversation_pairs(
    messages: list[dict],
) -> list[list[dict]]:
    """Group conversation messages into logical pairs that must stay together.

    A ``tool_calls`` assistant message and all immediately following ``tool``
    role messages form a single group.  All other messages form groups of one.
    """
    groups: list[list[dict]] = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            # Collect this assistant message plus all consecutive tool-result messages.
            group: list[dict] = [msg]
            i += 1
            while i < len(messages) and messages[i].get("role") == "tool":
                group.append(messages[i])
                i += 1
            groups.append(group)
        else:
            groups.append([msg])
            i += 1
    return groups


def truncate_messages(
    messages: list[dict],
    budget: ContextBudget,
) -> list[dict]:
    """Truncate message history to fit within budget.

    Keeps the system prompt (if present) and the most-recent messages.
    Drops oldest *complete logical groups* first so that an assistant
    ``tool_calls`` message is never separated from its ``tool`` responses.
    """
    if not messages:
        return []

    system_msg = messages[0] if messages[0].get("role") == "system" else None
    conversation = messages[1:] if system_msg else messages

    budget.system_prompt_tokens = (
        estimate_tokens(system_msg.get("content", "")) if system_msg else 0
    )

    token_limit = budget.max_tokens - budget.reserved_for_response

    # Group conversation messages into logical pairs.
    groups = _group_conversation_pairs(conversation)

    # Walk from newest to oldest, keeping groups that fit.
    total_tokens = budget.system_prompt_tokens
    kept_groups: list[list[dict]] = []

    for group in reversed(groups):
        group_tokens = sum(
            estimate_tokens(m.get("content", "") or "")
            for m in group
        )
        if total_tokens + group_tokens > token_limit:
            break
        total_tokens += group_tokens
        kept_groups.insert(0, group)

    budget.message_tokens = total_tokens - budget.system_prompt_tokens

    result: list[dict] = []
    if system_msg:
        result.append(system_msg)
    for group in kept_groups:
        result.extend(group)
    return result


def truncate_context(context: str, budget: ContextBudget) -> str:
    """Truncate context string to fit within budget."""
    context_tokens = estimate_tokens(context)
    budget.context_tokens = context_tokens

    if not budget.is_over_budget:
        return context

    available_chars = int(budget.available_tokens / TOKENS_PER_CHAR_ESTIMATE)
    if available_chars <= 0:
        return ""

    lines = context.splitlines()
    result = []
    current_length = 0

    for line in lines:
        line_length = len(line) + 1
        if current_length + line_length > available_chars:
            break
        result.append(line)
        current_length += line_length

    if len(result) < len(lines):
        result.append(f"\n... (truncated, {len(lines) - len(result)} more sections)")

    return "\n".join(result)


def summarize_conversation(
    messages: list[dict[str, str]],
    max_summary_length: int = 500,
) -> str:
    """Create a text summary of conversation history.

    This is a simple extraction-based summary. For better results,
    use an LLM to summarize.
    """
    if len(messages) <= 3:
        return ""

    topics = []
    for msg in messages[1:-1]:
        content = msg.get("content", "")[:100]
        if content:
            topics.append(f"{msg['role']}: {content}")

    summary = "\n".join(topics[-5:])
    if len(summary) > max_summary_length:
        summary = summary[:max_summary_length] + "..."

    return summary
