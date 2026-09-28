"""Presentation helpers shared by the workflow pages.

The app is themed through `.streamlit/config.toml`. The scoped CSS below
covers only the pieces Streamlit has no native element for - the gradient
hero band, the numbered step strip and the feature tiles - and every rule
is namespaced under `bj-` so nothing leaks into Streamlit's own classes.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from agent.state import is_done

STYLES = """
<style>
:root {
  --bj-brand-a: #6D3BF5;
  --bj-brand-b: #5B6CF9;
  --bj-brand-c: #2FA6EE;
  --bj-surface: #131A2B;
  --bj-line: #242E45;
  --bj-muted: #94A3B8;
}

/* ---------------------------------------------------------- hero band */
.bj-hero {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  padding: 30px 34px;
  margin: 2px 0 18px;
  background: linear-gradient(115deg, var(--bj-brand-a) 0%, var(--bj-brand-b) 48%, var(--bj-brand-c) 100%);
  box-shadow: 0 18px 40px -22px rgba(109, 59, 245, 0.85);
}
.bj-hero::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(120% 140% at 88% -20%, rgba(255,255,255,0.28) 0%, rgba(255,255,255,0) 55%);
  pointer-events: none;
}
.bj-hero-eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.78);
  margin-bottom: 8px;
}
.bj-hero h1 {
  margin: 0;
  font-size: 34px;
  line-height: 1.15;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #FFFFFF;
}
.bj-hero p {
  margin: 10px 0 0;
  max-width: 76ch;
  font-size: 15px;
  line-height: 1.55;
  color: rgba(255,255,255,0.90);
}
.bj-hero.bj-hero-slim { padding: 20px 26px; margin-bottom: 14px; }
.bj-hero.bj-hero-slim h1 { font-size: 25px; }
.bj-hero.bj-hero-slim p { font-size: 14px; margin-top: 6px; }

.bj-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; position: relative; z-index: 1; }
.bj-pill {
  padding: 4px 13px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 500;
  color: #FFFFFF;
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.26);
  backdrop-filter: blur(2px);
}

/* ------------------------------------------------------- step strip */
.bj-steps { display: flex; flex-wrap: wrap; align-items: stretch; gap: 8px; margin: 4px 0 6px; }
.bj-step {
  flex: 1 1 150px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 13px 15px;
  border-radius: 12px;
  background: var(--bj-surface);
  border: 1px solid var(--bj-line);
  transition: border-color 0.15s ease;
}
.bj-step.is-done { border-color: rgba(52, 211, 153, 0.55); }
.bj-step-num {
  flex: none;
  width: 27px;
  height: 27px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 12.5px;
  font-weight: 700;
  color: #FFFFFF;
  background: linear-gradient(140deg, var(--bj-brand-a), var(--bj-brand-c));
}
.bj-step.is-done .bj-step-num { background: linear-gradient(140deg, #10B981, #34D399); }
.bj-step-label { font-size: 13.5px; font-weight: 600; color: #E6EAF3; line-height: 1.25; }
.bj-step-note { font-size: 11.5px; color: var(--bj-muted); margin-top: 1px; }
.bj-arrow { display: grid; place-items: center; color: #3C4A66; font-size: 17px; flex: none; padding: 0 1px; }

/* ----------------------------------------------------- feature tiles */
.bj-features { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 4px; }
.bj-feature {
  flex: 1 1 200px;
  padding: 17px 18px;
  border-radius: 14px;
  background: var(--bj-surface);
  border: 1px solid var(--bj-line);
}
.bj-feature-icon { font-size: 20px; line-height: 1; margin-bottom: 10px; }
.bj-feature h4 { margin: 0 0 6px; font-size: 14.5px; font-weight: 650; color: #E6EAF3; }
.bj-feature p { margin: 0; font-size: 12.8px; line-height: 1.5; color: var(--bj-muted); }

/* ------------------------------------------------- sidebar sections */
.bj-sec {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 14px 0 6px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--bj-muted);
}
.bj-sec-num {
  width: 17px; height: 17px;
  border-radius: 50%;
  display: grid; place-items: center;
  font-size: 10px;
  color: #FFFFFF;
  background: linear-gradient(140deg, var(--bj-brand-a), var(--bj-brand-c));
  letter-spacing: 0;
}
</style>
"""


def inject_styles() -> None:
    """Called once per rerun from the entry point, before any page renders."""
    st.html(STYLES)


def _pills(items: list[str]) -> str:
    if not items:
        return ""
    chips = "".join(f'<span class="bj-pill">{item}</span>' for item in items)
    return f'<div class="bj-pills">{chips}</div>'


def hero(title: str, subtitle: str, eyebrow: str = "", pills: list[str] | None = None, slim: bool = False) -> None:
    """The gradient brand band that opens every page."""
    classes = "bj-hero bj-hero-slim" if slim else "bj-hero"
    eyebrow_html = f'<div class="bj-hero-eyebrow">{eyebrow}</div>' if eyebrow else ""
    st.html(
        f'<div class="{classes}">{eyebrow_html}'
        f"<h1>{title}</h1><p>{subtitle}</p>{_pills(pills or [])}</div>"
    )


def page_header(title: str, subtitle: str, icon: str = "", eyebrow: str = "") -> None:
    """Slim hero used by the five workflow pages."""
    hero(title, subtitle, eyebrow=eyebrow, slim=True)


def step_strip(steps: list[tuple[str, str, str]]) -> None:
    """Numbered pipeline strip with arrows between the stages."""
    blocks: list[str] = []
    for index, (key, label, note) in enumerate(steps, start=1):
        done = is_done(key)
        state = " is-done" if done else ""
        mark = "&#10003;" if done else str(index)
        blocks.append(
            f'<div class="bj-step{state}"><div class="bj-step-num">{mark}</div>'
            f'<div><div class="bj-step-label">{label}</div>'
            f'<div class="bj-step-note">{note}</div></div></div>'
        )
    joined = '<div class="bj-arrow">&#8594;</div>'.join(blocks)
    st.html(f'<div class="bj-steps">{joined}</div>')


def feature_tiles(tiles: list[tuple[str, str, str]]) -> None:
    """Each tile is (icon, heading, description)."""
    cards = "".join(
        f'<div class="bj-feature"><div class="bj-feature-icon">{icon}</div>'
        f"<h4>{heading}</h4><p>{text}</p></div>"
        for icon, heading, text in tiles
    )
    st.html(f'<div class="bj-features">{cards}</div>')


def sidebar_section(number: str, label: str) -> None:
    st.html(f'<div class="bj-sec"><span class="bj-sec-num">{number}</span>{label}</div>')


# ------------------------------------------------------------- native helpers


def require(step: str, message: str, page: str) -> bool:
    """Gate a page behind an earlier stage. Returns True when it may proceed."""
    if is_done(step):
        return True
    st.info(message, icon=":material/arrow_forward:")
    if st.button("Take me there", icon=":material/arrow_outward:", type="primary"):
        st.switch_page(page)
    return False


def kpi_row(items: list[tuple[str, str, str | None]]) -> None:
    """Each item is (label, value, help text)."""
    with st.container(horizontal=True):
        for label, value, extra in items:
            st.metric(label, value, help=extra, border=True)


def flag_list(flags: list[dict[str, str]]) -> None:
    icons = {
        "success": ":material/check_circle:",
        "info": ":material/info:",
        "warning": ":material/warning:",
        "error": ":material/error:",
    }
    renderers = {"success": st.success, "info": st.caption, "warning": st.warning, "error": st.error}
    for flag in flags:
        level = flag.get("level", "info")
        render = renderers.get(level, st.caption)
        if render is st.caption:
            render(flag["text"])
        else:
            render(flag["text"], icon=icons.get(level))


def preview(df: pd.DataFrame, rows: int = 50, key: str | None = None) -> None:
    st.dataframe(df.head(rows), hide_index=True, height=340, key=key)
    st.caption(f"Showing the first {min(rows, len(df)):,} of {len(df):,} rows.")


def model_note(used_model: bool) -> None:
    if used_model:
        st.caption(f"Written by {st.session_state.model}, grounded in the computed profile above.")
    else:
        st.caption("Written by the deterministic statistics engine — add an API key in the sidebar for model-written commentary.")
