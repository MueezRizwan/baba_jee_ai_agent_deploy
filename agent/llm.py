"""The reasoning core of Baba_Jee: a thin, defensive OpenAI wrapper.

Design rules:

* The key is read from the sidebar first, then ``st.secrets``, then the
  environment - so the same code runs locally and on Streamlit Cloud.
* Every call degrades gracefully. If no key is configured, or the API
  errors, the caller gets a clear message instead of a traceback, and the
  app falls back to its deterministic rule-based commentary.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import streamlit as st

try:  # pragma: no cover - import guard for slim deployments
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1-mini",
    "gpt-4.1",
    "o4-mini",
]

SYSTEM_PROMPT = """You are Baba_Jee, a seasoned data analyst with the warmth of a wise elder \
and the rigour of a statistician.

Rules you never break:
- Ground every statement in the dataset facts you are given. If the facts do not support a
  claim, say so plainly instead of inventing numbers.
- Quote concrete figures (counts, percentages, correlations) when you make a point.
- Flag data-quality risks: small samples, heavy missingness, extreme outliers, constant or
  near-duplicate columns, suspicious cardinality.
- Correlation is not causation, and you say so whenever someone edges toward causal language.
- Write in clean markdown. Be concise: short paragraphs and tight bullets, no filler, no
  restating the question back to the user.
"""


def resolve_key() -> str:
    """Sidebar key > st.secrets > environment."""
    key = (st.session_state.get("api_key") or "").strip()
    if key:
        return key
    try:
        secret = st.secrets.get("OPENAI_API_KEY", "")
        if secret:
            return str(secret).strip()
    except Exception:  # secrets.toml absent is perfectly normal
        pass
    return (os.environ.get("OPENAI_API_KEY") or "").strip()


def default_model() -> str:
    try:
        return str(st.secrets.get("OPENAI_MODEL", MODELS[0]))
    except Exception:
        return os.environ.get("OPENAI_MODEL", MODELS[0])


def is_ready() -> bool:
    """True when the agent can actually reach a model."""
    return bool(OpenAI) and bool(resolve_key()) and bool(st.session_state.get("use_llm", True))


@st.cache_resource(show_spinner=False)
def _client(key: str):
    return OpenAI(api_key=key)


def get_client():
    key = resolve_key()
    if not OpenAI:
        raise RuntimeError("The `openai` package is not installed. Run: pip install -r requirements.txt")
    if not key:
        raise RuntimeError("No OpenAI API key found. Add one in the sidebar or in Streamlit secrets.")
    return _client(key)


def _params() -> dict[str, Any]:
    model = st.session_state.get("model") or default_model()
    params: dict[str, Any] = {"model": model}
    # Reasoning models reject a custom temperature; everything else accepts it.
    if not model.startswith(("o1", "o3", "o4")):
        params["temperature"] = float(st.session_state.get("temperature", 0.2))
    return params


def complete(prompt: str, system: str = SYSTEM_PROMPT, history: list[dict] | None = None) -> str:
    """One-shot completion. Raises RuntimeError with a readable message."""
    client = get_client()
    messages = [{"role": "system", "content": system}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": prompt})
    try:
        response = client.chat.completions.create(messages=messages, **_params())
    except Exception as exc:  # surface provider errors as plain text
        raise RuntimeError(f"The model call failed: {exc}") from exc
    return (response.choices[0].message.content or "").strip()


def stream(prompt: str, system: str = SYSTEM_PROMPT, history: list[dict] | None = None) -> Iterator[str]:
    """Token generator for ``st.write_stream``."""
    client = get_client()
    messages = [{"role": "system", "content": system}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": prompt})
    try:
        chunks = client.chat.completions.create(messages=messages, stream=True, **_params())
        for chunk in chunks:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as exc:
        raise RuntimeError(f"The model call failed: {exc}") from exc
