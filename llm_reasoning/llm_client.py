"""Thin client for the LLM reasoning layer (Layer 3).

Supports three interchangeable providers, tried in this order if multiple
keys are set: Anthropic (ANTHROPIC_API_KEY), Google Gemini (GOOGLE_API_KEY),
and OpenAI (OPENAI_API_KEY). The `anthropic`/`google-genai`/`openai` SDKs are
imported lazily so the rest of the framework works without any of them
installed, and `is_available()` lets callers check before wasting time
building a prompt.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5")
DEFAULT_OPENAI_MODEL = os.environ.get("LLM_MODEL_OPENAI", "gpt-4o")
DEFAULT_GEMINI_MODEL = os.environ.get("LLM_MODEL_GEMINI", "gemini-2.5-flash")
DEFAULT_MAX_TOKENS = 4096


def is_available() -> bool:
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )


def complete(system_prompt: str, user_prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Sends a prompt to whichever provider has an API key configured and returns the raw text response.

    Provider preference order: Anthropic, then Gemini, then OpenAI. Raises RuntimeError if none is
    configured or the call fails, so callers can decide how to degrade (e.g. skip Layer 3 for this file).
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _complete_anthropic(system_prompt, user_prompt, max_tokens)
    if os.environ.get("GOOGLE_API_KEY"):
        return _complete_gemini(system_prompt, user_prompt, max_tokens)
    if os.environ.get("OPENAI_API_KEY"):
        return _complete_openai(system_prompt, user_prompt, max_tokens)
    raise RuntimeError(
        "No LLM API key configured. Set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or OPENAI_API_KEY in your .env."
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


def _complete_gemini(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "The `google-genai` package is not installed. Run `pip install google-genai`."
        ) from exc

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    try:
        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    return response.text or ""


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