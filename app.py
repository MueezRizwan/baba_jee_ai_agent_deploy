"""Baba_Jee launcher.

Both of these work, and both open the browser by themselves:

    streamlit run app.py     <- the normal Streamlit command
    python app.py            <- plain Python; this file starts Streamlit for you

The canonical entry point is `streamlit_app.py` - that is the filename
Streamlit Community Cloud looks for by default, so it stays the real app.
This module only decides how it should be started.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
MAIN = HERE.with_name("streamlit_app.py")


def running_inside_streamlit() -> bool:
    """True when a Streamlit server is already executing this script."""
    try:
        from streamlit.runtime import exists

        return exists()
    except Exception:
        return False


def launch() -> None:
    """Start the Streamlit server on this file and open the browser."""
    from streamlit.web import cli

    sys.argv = [
        "streamlit",
        "run",
        str(HERE),
        "--server.port=8501",
        "--server.headless=false",  # open the browser automatically
    ]
    sys.exit(cli.main())


if running_inside_streamlit():
    # Started with `streamlit run app.py` - just run the real app.
    runpy.run_path(str(MAIN), run_name="__main__")
else:
    # Started with `python app.py` - boot the server ourselves.
    launch()
