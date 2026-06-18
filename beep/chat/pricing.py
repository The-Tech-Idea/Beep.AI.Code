"""Model pricing hints for cost estimation and budget guardrails."""

from __future__ import annotations

MODEL_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "o1": (15.00, 60.00),
    "o3-mini": (1.10, 4.40),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
    "qwen2.5-coder": (0.00, 0.00),
    "codellama": (0.00, 0.00),
}

DEFAULT_PRICE_PER_MILLION = (3.00, 15.00)


def _model_price(model: str | None) -> tuple[float, float]:
    if model is None:
        return DEFAULT_PRICE_PER_MILLION
    model_lower = model.lower()
    for key in sorted(MODEL_PRICES, key=len, reverse=True):
        if key in model_lower:
            return MODEL_PRICES[key]
    return DEFAULT_PRICE_PER_MILLION


def estimate_cost(token_count: int, model: str | None = None) -> float:
    input_price, output_price = _model_price(model)
    avg_price = (input_price + output_price) / 2
    return (token_count / 1_000_000) * avg_price


def price_hint(model: str | None = None) -> str:
    inp, out = _model_price(model)
    if inp == 0 and out == 0:
        return "Local model — no API cost"
    return f"${inp:.2f}/M input, ${out:.2f}/M output"
