"""@mention parser for subagent routing in chat input.

Detects leading @explore, @plan, @general mentions and returns
the subagent type and remaining message for routing.
"""

from __future__ import annotations

from dataclasses import dataclass

VALID_MENTIONS = frozenset({"explore", "plan", "general"})


@dataclass
class MentionMatch:
    subagent_type: str
    remainder: str


def parse_mention(user_input: str) -> MentionMatch | None:
    text = user_input.strip()
    if not text.startswith("@"):
        return None

    first_space = text.find(" ")
    if first_space == -1:
        mention_part = text[1:]
        remainder = ""
    else:
        mention_part = text[1:first_space]
        remainder = text[first_space + 1 :].strip()

    mention_lower = mention_part.lower()

    if mention_lower not in VALID_MENTIONS:
        return None

    return MentionMatch(subagent_type=mention_lower, remainder=remainder)


def build_mention_guidance(match: MentionMatch) -> str:
    guidance_map = {
        "explore": (
            "You are functioning as an explore subagent. "
            "Your task is to search the codebase and report findings. "
            "Use tools like search, file_read, semantic_search, "
            "list_directory, and code_snippet_list. Do not modify any files."
        ),
        "plan": (
            "You are functioning as a plan subagent. "
            "Your task is to analyze the request and produce a structured plan. "
            "Break down the work into clear steps. Do not modify any files."
        ),
        "general": (
            "You are functioning as a general subagent. "
            "Your task is to assist with the given request using available tools. "
        ),
    }
    return guidance_map.get(match.subagent_type, "")
