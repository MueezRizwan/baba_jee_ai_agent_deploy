"""Session state and workflow gating for Baba_Jee."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

STEPS: list[tuple[str, str, str]] = [
    ("upload", "Data upload", ":material/upload_file:"),
    ("preprocess", "Data preprocessing", ":material/cleaning_services:"),
    ("analysis", "Data analysis", ":material/query_stats:"),
    ("visualize", "Data visualization", ":material/insights:"),
    ("report", "Final report", ":material/description:"),
]

_DEFAULTS: dict[str, object] = {
    # Workflow artefacts
    "raw_df": None,
    "clean_df": None,
    "source_name": None,
    "preprocess_log": [],
    "analysis": None,
    "insights": None,
    "used_model": False,
    "charts": [],
    "chart_notes": {},
    "report_md": None,
    # Agent configuration
    "api_key": "",
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "use_llm": True,
    # Conversation with the agent
    "messages": [],
    # Progress flags
    "done": {key: False for key, _, _ in STEPS},
}


def init_state() -> None:
    """Create every key the app relies on, exactly once per session."""
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value


def mark_done(step: str, value: bool = True) -> None:
    st.session_state.done[step] = value


def is_done(step: str) -> bool:
    return bool(st.session_state.done.get(step, False))


def reset_from(step: str) -> None:
    """Invalidate a step and everything downstream of it."""
    order = [key for key, _, _ in STEPS]
    if step not in order:
        return
    downstream = order[order.index(step):]
    clear_map = {
        "upload": ("raw_df", "source_name"),
        "preprocess": ("clean_df", "preprocess_log"),
        "analysis": ("analysis", "insights"),
        "visualize": ("charts", "chart_notes"),
        "report": ("report_md",),
    }
    for name in downstream:
        st.session_state.done[name] = False
        for key in clear_map.get(name, ()):  # noqa: B007
            st.session_state[key] = _DEFAULTS[key]
            if isinstance(_DEFAULTS[key], (dict, list)):
                st.session_state[key] = _DEFAULTS[key].copy()


def active_df():
    """The dataframe later stages should work on (cleaned if available)."""
    return st.session_state.clean_df if st.session_state.clean_df is not None else st.session_state.raw_df


@dataclass(frozen=True)
class Progress:
    completed: int
    total: int

    @property
    def ratio(self) -> float:
        return self.completed / self.total if self.total else 0.0

    @property
    def label(self) -> str:
        return f"{self.completed} of {self.total} stages complete"


def progress() -> Progress:
    return Progress(sum(1 for key, _, _ in STEPS if is_done(key)), len(STEPS))
