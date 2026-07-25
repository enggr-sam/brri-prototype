"""Estimate Gemini API spend from token usage metadata."""

from __future__ import annotations

# USD per 1M tokens (approximate — update if Google changes pricing).
_MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-flash-lite": {"input": 0.075, "output": 0.30},
    "gemini-flash-latest": {"input": 0.10, "output": 0.40},
    "gemini-flash-lite-latest": {"input": 0.075, "output": 0.30},
}

_DEFAULT_PRICING = {"input": 1.0, "output": 3.0}


def _pricing_for_model(model: str) -> dict[str, float]:
    model_lower = model.lower()
    for key, prices in _MODEL_PRICING.items():
        if key in model_lower:
            return prices
    return _DEFAULT_PRICING


def extract_usage(response) -> tuple[int, int]:
    """Return (input_tokens, output_tokens) from a Gemini response or chunk."""
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return 0, 0
    prompt = (
        getattr(meta, "prompt_token_count", None)
        or getattr(meta, "input_token_count", None)
        or 0
    )
    output = (
        getattr(meta, "candidates_token_count", None)
        or getattr(meta, "output_token_count", None)
        or 0
    )
    return int(prompt), int(output)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = _pricing_for_model(model)
    cost = (input_tokens / 1_000_000) * prices["input"]
    cost += (output_tokens / 1_000_000) * prices["output"]
    return round(cost, 6)


def merge_usage(
    a: tuple[int, int, float],
    b: tuple[int, int, float],
) -> tuple[int, int, float]:
    return (a[0] + b[0], a[1] + b[1], round(a[2] + b[2], 6))
