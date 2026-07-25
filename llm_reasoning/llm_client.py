"""Thin client for the LLM reasoning layer (Layer 3).

Primary provider is the Claude API (ANTHROPIC_API_KEY). An OpenAI fallback is
supported since the README lists "Claude API / OpenAI API" as interchangeable
options. The `anthropic`/`openai` SDKs are imported lazily so the rest of the
framework works without either installed, and `is_available()` lets callers
check before wasting time building a prompt.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5")
DEFAULT_OPENAI_MODEL = os.environ.get("LLM_MODEL_OPENAI", "gpt-4o")
DEFAULT_MAX_TOKENS = 4096


def is_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def complete(system_prompt: str, user_prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Sends a prompt to whichever provider has an API key configured and returns the raw text response.

    Prefers Anthropic if both keys are set. Raises RuntimeError if neither is configured or the
    call fails, so callers can decide how to degrade (e.g. skip Layer 3 for this file).
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _complete_anthropic(system_prompt, user_prompt, max_tokens)
    if os.environ.get("OPENAI_API_KEY"):
        return _complete_openai(system_prompt, user_prompt, max_tokens)
    raise RuntimeError(
        "No LLM API key configured. Set ANTHROPIC_API_KEY (preferred) or OPENAI_API_KEY in your .env."
    )


def _complete_anthropic(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("The `anthropic` package is not installed. Run `pip install -r requirements.txt`.") from exc

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    try:
        response = client.messages.create(
            model=DEFAULT_ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:
        raise RuntimeError(f"Anthropic API call failed: {exc}") from exc

    return "".join(block.text for block in response.content if getattr(block, "type", None) == "text")


def _complete_openai(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    try:
        import openai
    except ImportError as exc:
        raise RuntimeError("The `openai` package is not installed. Run `pip install -r requirements.txt`.") from exc

    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    try:
        response = client.chat.completions.create(
            model=DEFAULT_OPENAI_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI API call failed: {exc}") from exc

    return response.choices[0].message.content or ""
