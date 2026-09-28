# Baba_Jee

**Your elder in data — upload it, and let Baba Jee read it.**

Baba_Jee is an AI data-analysis agent built with Streamlit. Give it a CSV, Excel or JSON file and it walks a fixed five-stage pipeline, showing its work at every step:

```
Data upload → Data preprocessing → Data analysis → Data visualization → Final report
```

Statistics are computed in Python. The language model is used only to *explain* those statistics — it never invents numbers, and it never sees your raw rows. If no API key is configured, the agent falls back to a deterministic rule-based writer and every stage still works.

📘 **New here? Read [GUIDE.md](GUIDE.md)** — the step-by-step user guide.

---

## Quick start (local)

```bash
# 1. Clone / open the project folder
cd ai_agent_deploy

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
streamlit run streamlit_app.py
```

The app opens at <http://localhost:8501>.

### Adding an OpenAI key

Three options, checked in this order:

| Where | How |
| --- | --- |
| **Sidebar** | Open *① Connect OpenAI* → paste the key. Lives in the browser session only. |
| **Secrets file** | Copy `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` and fill it in. |
| **Environment** | `set OPENAI_API_KEY=sk-...` (Windows) / `export OPENAI_API_KEY=sk-...` |

Without a key the app runs in **local mode**: profiling, cleaning, statistics, charts and the report all still work; only the narrative prose switches to the rule-based writer.

---

## Deploying to Streamlit Community Cloud

1. Push this folder to a **public GitHub repository**. `.gitignore` already excludes `.venv/`, `.env` and `.streamlit/secrets.toml`.
2. Go to <https://share.streamlit.io> → **New app**.
3. Point it at your repo and set:
   - **Main file path**: `streamlit_app.py`
   - **Python version**: 3.11 or newer
4. Open **Advanced settings → Secrets** and paste:

   ```toml
   OPENAI_API_KEY = "sk-your-key-here"
   OPENAI_MODEL = "gpt-4o-mini"
   ```

5. Deploy. `requirements.txt` is picked up automatically.

**Do not commit your API key.** If you skip the secret entirely the app still deploys and runs in local mode — which is a reasonable way to share a public demo without paying for anyone else's tokens.

---

## Project layout

```
streamlit_app.py            Entry point: navigation, shared state, agent control panel
app_pages/
  home.py                   Overview and workflow status
  upload.py                 Stage 1 — file parsing, profiling, arrival checks
  preprocess.py             Stage 2 — cleaning plan and audit trail
  analysis.py               Stage 3 — statistics, correlations, outliers, interpretation
  visualize.py              Stage 4 — recommended charts plus a manual chart builder
  report.py                 Stage 5 — assembled markdown report and downloads
  chat.py                   Ask Baba Jee — grounded Q&A about the loaded dataset
agent/
  __init__.py               Agent identity and version
  state.py                  Session state, workflow gating, progress
  llm.py                    OpenAI wrapper — key resolution, streaming, graceful failure
  profiling.py              Dataframe → compact JSON profile (what the model sees)
  preprocessing.py          Logged, reversible cleaning operations
  analysis.py               Descriptive stats, correlations, outliers, quality flags
  charts.py                 Chart recommendation + Altair rendering
  report.py                 Markdown report assembly
  export.py                 Markdown -> Microsoft Word (.docx) conversion
  qa.py                     Rule-based question answering for the chat page
  samples.py                The bundled sample-dataset library
  ui.py                     Shared presentation helpers
.streamlit/config.toml      Theme (colours, fonts, radii, chart palette)
sample_data/                11 bundled demo datasets, each with deliberate flaws
tools/make_samples.py       Regenerates every sample dataset
requirements.txt            Deployment dependencies
```

### Design decisions worth knowing

- **The model never sees raw rows.** `agent/profiling.py` reduces the dataframe to aggregate statistics, and only that JSON is sent. This keeps requests small, costs predictable, and record-level data in your session.
- **Every stage degrades gracefully.** `llm.is_ready()` gates every model call, and each caller has a deterministic fallback — including the chat page, where `agent/qa.py` answers from the computed statistics when no key is present.
- **Preprocessing always restarts from the original upload**, so re-running the cleaning plan can never compound its own edits.
- **Charts are recommended, not hardcoded.** `charts.recommend()` scores candidates from the column types and the correlation results, so suggestions change with the data.
- **Theming lives in `config.toml`** — colours, fonts, radii and the chart palette — so it survives Streamlit upgrades and applies consistently to every element. The only CSS in the app is the `bj-` namespaced block in `agent/ui.py`, covering the three things Streamlit has no native element for: the gradient hero band, the numbered step strip and the feature tiles.

---

## Extending the agent

| To change | Edit |
| --- | --- |
| Colours, fonts, chart palette | `.streamlit/config.toml` |
| Hero band, step strip, feature tiles | `STYLES` in `agent/ui.py` |
| The agent's voice and rules | `SYSTEM_PROMPT` in `agent/llm.py` |
| Available models | `MODELS` in `agent/llm.py` |
| A new cleaning step | Add a `(df) -> (df, log_line)` function in `agent/preprocessing.py`, then wire it into `run_pipeline` |
| A new chart type | Add a branch in `charts.build()` and a candidate in `charts.recommend()` |
| Report sections | `agent/report.py` |
| Word document styling | `agent/export.py` |
| Chat answers without a key | `INTENTS` and the handlers in `agent/qa.py` |
| The sample library | `LIBRARY` in `agent/samples.py`, then `python tools/make_samples.py` |

---

## Requirements

Python 3.10+ and the packages in `requirements.txt`. Tested on Python 3.14 with Streamlit 1.64, pandas 3.0 and openai 3.19.

## Licence

Use it, fork it, ship it.
