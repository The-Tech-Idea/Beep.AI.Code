"""Token-aware context trimming for the LangGraph agent runtime.

Uses tiktoken (when available) for accurate token counting with fallback
to character-based estimation. Implements intelligent trimming that preserves
system prompt, recent tool call/result pairs, and injects a summary placeholder
when history is truncated.
"""

from __future__ import annotations

from typing import Any

DEFAULT_TOKEN_BUDGET = 60_000  # ~80% of an 80k context model
DEFAULT_SYSTEM_PROMPT_PRESERVED = True


def _load_tiktoken() -> Any | None:
    """Import tiktoken lazily; returns None if not installed."""
    try:
        import tiktoken

        return tiktoken
    except ImportError:
        return None


def _estimate_token_count(messages: list[dict[str, Any]]) -> int:
    """Rough token count estimate (4 chars ≈ 1 token for English text)."""
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        tool_calls = msg.get("tool_calls", [])
        for tc in tool_calls:
            args = tc.get("function", {}).get("arguments", "{}")
            total_chars += len(str(args))
    return total_chars // 4


def _count_tokens_tiktoken(
    messages: list[dict[str, Any]], encoding_name: str = "cl100k_base"
) -> int:
    """Count tokens using tiktoken for accurate measurement."""
    tiktoken = _load_tiktoken()
    if tiktoken is None:
        return _estimate_token_count(messages)

    try:
        enc = tiktoken.get_encoding(encoding_name)
    except Exception:
        return _estimate_token_count(messages)

    total = 0
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "") or ""
        if isinstance(content, str):
            total += len(enc.encode(role))
            total += len(enc.encode(content))
        tool_calls = msg.get("tool_calls", [])
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", "{}")
            total += len(enc.encode(name))
            total += len(enc.encode(str(args)))
    # LangChat adds ~4 tokens per message for formatting
    total += len(messages) * 4
    return total


def count_tokens(messages: list[dict[str, Any]]) -> int:
    """Count tokens in a message list, using tiktoken if available."""
    return _count_tokens_tiktoken(messages)


def should_trim(
    messages: list[dict[str, Any]],
    *,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> bool:
    """Check if message history exceeds the token budget."""
    return count_tokens(messages) > token_budget


def trim_messages(
    messages: list[dict[str, Any]],
    *,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    preserve_system: bool = DEFAULT_SYSTEM_PROMPT_PRESERVED,
) -> list[dict[str, Any]]:
    """Trim message history to fit within the token budget.

    Strategy:
    1. Always preserve system prompt (if present)
    2. Remove oldest tool call/result pairs first (they come in pairs)
    3. If still over budget, remove oldest user/assistant exchanges
    4. Insert a summary placeholder when trimming occurred

    Args:
        messages: Full message history
        token_budget: Maximum tokens allowed
        preserve_system: Whether to always keep the system message

    Returns:
        Trimmed message list
    """
    original_count = len(messages)
    if original_count <= 2:
        return messages

    system_msg = None
    working = list(messages)

    if preserve_system and working and working[0].get("role") == "system":
        system_msg = working.pop(0)

    # Remove oldest message pairs (tool_call + tool_result or user + assistant)
    while (
        len(working) > 2
        and count_tokens([system_msg] + working if system_msg else working) > token_budget
    ):
        # Find the first complete pair to remove
        removed = False
        for i in range(0, len(working) - 1):
            m1 = working[i]
            m2 = working[i + 1]
            # Remove tool call + tool result pair
            if m1.get("role") == "assistant" and m1.get("tool_calls") and m2.get("role") == "tool":
                working.pop(i)
                working.pop(i)
                removed = True
                break
            # Remove user + assistant pair (but not if assistant has tool_calls)
            if (
                m1.get("role") == "user"
                and m2.get("role") == "assistant"
                and not m2.get("tool_calls")
            ):
                working.pop(i)
                working.pop(i)
                removed = True
                break
        if not removed:
            # Fallback: remove oldest single message
            working.pop(0)

    if len(working) < len(messages) - (1 if system_msg else 0):
        # Insert summary placeholder
        placeholder = {
            "role": "user",
            "content": "[Previous conversation truncated to fit context window. Earlier tool calls and responses have been removed.]",
        }
        insert_idx = 1 if system_msg else 0
        working.insert(insert_idx, placeholder)

    if system_msg:
        return [system_msg] + working
    return working
