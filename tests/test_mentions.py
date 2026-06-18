"""Tests for @mention parser."""

from __future__ import annotations

from beep.chat.mentions import MentionMatch, build_mention_guidance, parse_mention


class TestParseMention:
    def test_explore_mention(self) -> None:
        match = parse_mention("@explore find the auth flow")
        assert match is not None
        assert match.subagent_type == "explore"
        assert match.remainder == "find the auth flow"

    def test_plan_mention(self) -> None:
        match = parse_mention("@plan design the cache")
        assert match is not None
        assert match.subagent_type == "plan"
        assert match.remainder == "design the cache"

    def test_general_mention(self) -> None:
        match = parse_mention("@general fix all bugs")
        assert match is not None
        assert match.subagent_type == "general"
        assert match.remainder == "fix all bugs"

    def test_mention_no_remainder(self) -> None:
        match = parse_mention("@explore")
        assert match is not None
        assert match.subagent_type == "explore"
        assert match.remainder == ""

    def test_case_insensitive(self) -> None:
        match = parse_mention("@EXPLORE something")
        assert match is not None
        assert match.subagent_type == "explore"
        assert match.remainder == "something"

    def test_no_mention(self) -> None:
        assert parse_mention("hello world") is None

    def test_not_a_mention(self) -> None:
        assert parse_mention("this is @explore something") is None

    def test_unknown_mention_type(self) -> None:
        assert parse_mention("@unknown do stuff") is None

    def test_email_not_mention(self) -> None:
        match = parse_mention("ask @explore to help")
        assert match is None


class TestBuildGuidance:
    def test_explore_guidance(self) -> None:
        match = MentionMatch(subagent_type="explore", remainder="test")
        guidance = build_mention_guidance(match)
        assert "explore subagent" in guidance.lower()
        assert "do not modify" in guidance.lower()

    def test_plan_guidance(self) -> None:
        match = MentionMatch(subagent_type="plan", remainder="test")
        guidance = build_mention_guidance(match)
        assert "plan subagent" in guidance.lower()
        assert "structured plan" in guidance.lower()

    def test_general_guidance(self) -> None:
        match = MentionMatch(subagent_type="general", remainder="test")
        guidance = build_mention_guidance(match)
        assert "general subagent" in guidance.lower()
