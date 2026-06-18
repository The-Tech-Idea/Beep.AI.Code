"""Tests for model pricing and cost estimation."""

from __future__ import annotations

from beep.chat.pricing import MODEL_PRICES, estimate_cost, price_hint


class TestModelPrices:
    def test_known_models(self) -> None:
        assert "gpt-4o" in MODEL_PRICES
        assert "claude-sonnet-4-20250514" in MODEL_PRICES
        assert "deepseek-chat" in MODEL_PRICES

    def test_local_models_zero_cost(self) -> None:
        assert MODEL_PRICES["qwen2.5-coder"][0] == 0
        assert MODEL_PRICES["qwen2.5-coder"][1] == 0

    def test_proprietary_models_nonzero(self) -> None:
        inp, out = MODEL_PRICES["gpt-4o"]
        assert inp > 0
        assert out > 0


class TestEstimateCost:
    def test_zero_tokens(self) -> None:
        assert estimate_cost(0) == 0.0

    def test_million_tokens_default(self) -> None:
        cost = estimate_cost(1_000_000)
        assert cost > 0

    def test_specific_model(self) -> None:
        cost = estimate_cost(1_000_000, "gpt-4o-mini")
        assert cost < estimate_cost(1_000_000, "gpt-4o")

    def test_local_model_no_cost(self) -> None:
        cost = estimate_cost(1_000_000, "qwen2.5-coder")
        assert cost == 0.0

    def test_model_fuzzy_match(self) -> None:
        cost = estimate_cost(1_000_000, "openrouter/claude-3-5-sonnet")
        assert cost > 0


class TestPriceHint:
    def test_default_hint(self) -> None:
        hint = price_hint()
        assert "$" in hint
        assert "/M" in hint

    def test_local_hint(self) -> None:
        hint = price_hint("qwen2.5-coder")
        assert "API cost" in hint or "Local" in hint

    def test_model_hint(self) -> None:
        hint = price_hint("gpt-4.1-mini")
        assert "$" in hint
