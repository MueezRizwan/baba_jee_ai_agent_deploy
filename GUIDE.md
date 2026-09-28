# Using Baba_Jee — a step-by-step guide

Baba_Jee is a data analyst you drive. You bring the file; he profiles it, cleans it, measures it, charts it and writes it up. You stay in control of every decision, and you can see exactly what he did at each step.

This guide assumes nothing about your background. If you can open a spreadsheet, you can use this agent.

---

## Before you start

**You need:** a data file — `.csv`, `.xlsx`, `.xls`, `.json`, `.parquet`, `.tsv` or `.txt`. Up to 200 MB.

**You do not need:** an OpenAI key. Without one, Baba Jee runs in **local mode** — all the statistics, cleaning, charts and the report still work, only the written commentary comes from built-in rules instead of a language model.

**With a key**, the commentary is written by the model, grounded in the numbers the app computed. Paste it in the sidebar under **① Connect OpenAI**, or set it in Streamlit secrets (see [README.md](README.md)).

### Reading the sidebar

| What you see | What it means |
| --- | --- |
| 🟢 `Connected · gpt-4o-mini` | A model is reachable; commentary will be model-written. |
| 🟠 `Local mode · no model key` | No key found; commentary comes from the rules engine. |
| Progress bar | How many of the five stages you have completed. |
| Checklist | Which stages are done (✓) and which are pending. |
| **Start a new session** | Clears everything and returns you to an empty state. |

---

## Stage 1 — Data upload

**What you do:** either drag your file into the **Upload your own file** tab, or open the **Sample library** tab and press **Load** on any of the eleven bundled datasets.

### The sample library

| Dataset | Rows | Good for |
| --- | --- | --- |
| Titanic passengers | 896 | Classification, missing-value strategy |
| Restaurant tips | 247 | Your first run — small and obvious |
| E-commerce orders | 1,215 | Revenue by category, shipping delay vs rating |
| Agriculture crop yield | 910 | Yield driven by rainfall, fertiliser and irrigation |
| Crypto coin prices | 1,338 | Time series, volatility, market co-movement |
| Employee attrition | 708 | Why people quit |
| Student performance | 656 | The clearest relationships in the library |
| Patient health records | 777 | Health screening, correlation vs causation |
| Daily weather | 1,845 | Seasonality and the best time-series charts |
| Housing prices | 831 | Price drivers and outlier listings |
| Retail sales | 409 | Showing off preprocessing |

Every one is synthetic but statistically realistic, and every one carries deliberate gaps, duplicates and outliers so each later stage has something real to do. Use the domain filter (All / Classic / Business / Science / Education / Finance) to narrow the list.

For CSVs you can pick a **delimiter** (leave it on *Detect automatically* unless the preview looks wrong). For Excel files you pick the **worksheet**.

**What Baba Jee does:** reads the file, infers each column's type, and reports what arrived.

**What to look at:**

- The five metric cards — rows, columns, missing cells, duplicate rows, memory.
- **Schema** tab — the detected type of every column, and a bar showing how much of it is missing.
- **First impressions** tab — structural problems spotted on arrival: heavily incomplete columns, zero-variance columns, and text columns that look like dates.

> **If the preview looks like nonsense** (everything crammed in one column), change the delimiter and re-upload.

---

## Stage 2 — Data preprocessing

**What you do:** tick the cleaning steps you want, then press **Run preprocessing**.

The steps are grouped into three columns:

**Structure**
- *Standardise column names* — `Order Date` becomes `order_date`. Recommended; it makes every later stage easier to read.
- *Trim whitespace in text* — collapses `"  Online  "` and `"Online"` into one value. Recommended.
- *Parse date-like columns* — turns text that looks like a date into a real date, so trends over time become possible.
- *Drop duplicate rows* — removes exact repeats.

**Missing data**
- *Numeric columns* — fill gaps with the median (safe default), mean, zero, or leave them missing.
- *Categorical columns* — fill with the most frequent value, with `"unknown"`, or leave them missing.
- *Drop mostly-empty columns* — removes columns above the missing-share slider (default 90%).

**Noise**
- *Drop zero-variance columns* — a column where every row is identical carries no information.
- *Remove outlier rows* — **off by default, and deliberately so.** Outliers are often the most interesting part of a dataset. Only turn this on when you know those values are errors.

**What to look at:** the **Audit trail** tab. Every step writes a plain-English line — *"Removed 9 duplicate row(s)"* — and that same trail is reproduced in the final report, so a reader can see exactly what changed.

> **You can re-run this as often as you like.** The pipeline always starts from your original upload, so it never compounds its own edits. Change your mind, re-run, compare the metric deltas against the upload.

---

## Stage 3 — Data analysis

**What you do:** set the **correlation reporting threshold** (0.5 is a sensible default — it reports moderate relationships and stronger), then press **Run analysis**.

**What Baba Jee does**, visibly, in three steps:

1. Profiles every column and its data quality.
2. Measures correlations between numeric columns and outliers using the 1.5×IQR rule.
3. Writes an interpretation of those numbers.

**What to look at:**

- **Findings** — the written interpretation, plus the data-quality flags. A caption under the text always tells you whether it was written by the model or the rules engine.
- **Descriptive statistics** — count, mean, standard deviation, min, quartiles, max for every numeric column.
- **Correlations** — the pairs that cleared your threshold, ranked by strength, with a full matrix in the expander.
- **Outliers** — which columns have unusual values, how many, and the fences that define "unusual".

### How to read a correlation

`r` runs from −1 to +1.

| \|r\| | Reading |
| --- | --- |
| 0.8 – 1.0 | Very strong |
| 0.6 – 0.8 | Strong |
| 0.4 – 0.6 | Moderate |
| below 0.4 | Weak — usually not worth acting on |

A **positive** r means the two columns rise together. A **negative** r means one rises as the other falls.

> **Correlation is not causation.** If marketing spend and revenue correlate at 0.97, that does not prove the spending caused the revenue — the spend may simply have been budgeted as a percentage of it. Baba Jee flags this every time, and so should you.

---

## Stage 4 — Data visualization

**What you do:** the agent proposes charts that fit the columns it actually found. Deselect any that don't earn their place; each one has a **Why this chart** expander explaining the reasoning.

Typical suggestions:

| Chart | Appears when | Tells you |
| --- | --- | --- |
| Line over time | A real date column exists | Direction and seasonality |
| Scatter | Two numeric columns correlate | The shape behind the correlation number |
| Bar by category | A category and a measure exist | Which groups lead and lag |
| Histogram | Any numeric column | Skew, spread and where outliers sit |
| Record count | Any category column | Class balance — vital before modelling |
| Correlation heatmap | Three or more numeric columns | Every numeric pair at once |

**Build your own chart:** the expander at the bottom lets you pick the type and the columns yourself. Press **Add to report** to include it.

Charts are interactive — hover for values, and use the chart's own menu to save a PNG if you want to paste figures into the report.

---

## Stage 5 — Final report

**What you do:** press **Generate report**.

**What you get**, in eight sections:

1. **Executive summary** — 4–6 action-oriented bullets, finding first.
2. **Data preparation** — the numbered audit trail from stage 2.
3. **Dataset structure** — which columns are numeric, categorical, datetime or text, plus descriptive statistics.
4. **Analysis** — the interpretation from stage 3.
5. **Correlations** — a ranked table with the causation caveat.
6. **Outliers** — counts, shares and fences.
7. **Visualizations** — each figure with its justification and what it shows.
8. **Data quality flags** — what a reader should be sceptical about.

**Three downloads:**
- **MS Word (.docx)** — a real Word document with styled headings, bullet and numbered lists and proper tables. Open it in Microsoft Word, Google Docs or LibreOffice and edit it like anything else.
- **Markdown (.md)** — plain text, pastes into Notion, GitHub or Confluence.
- **Cleaned data (.csv)** — the dataset exactly as the analysis saw it.

You can regenerate the report after changing any earlier stage.

---

## Ask Baba Jee

A chat page for questions the fixed pipeline doesn't answer: *"Where should I start?"*, *"What could go wrong with this data?"*, *"Suggest questions to ask."*

Six starter prompts appear before your first message. **This page works without an API key.** Without one, Baba Jee answers from the statistics he already computed — so every figure in the reply is real. He handles:

- where to start, correlations, risks, suggested questions
- missing values, outliers, dataset overview
- **any single column by name** — type *"tell me about revenue"* and you get its type, range, mean, median, skew, most frequent values and related columns

With a key, the same questions are answered by the model in open-ended prose, and you can ask anything.

**What the agent can see** is shown in an expander at the bottom: the aggregate profile of your dataset, and nothing else. Your individual rows are never sent to the model.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| *"Baba Jee could not parse that file"* | Wrong delimiter, or the file isn't really the format its extension claims. Try another delimiter or re-export from your source tool. |
| Preview shows one giant column | Change the delimiter on the upload page. |
| A page says "Baba Jee needs a dataset first" | The stages run in order. Press the button it offers to jump to the missing stage. |
| Correlations tab says no pair qualified | Lower the threshold, or accept that the numeric columns genuinely move independently. |
| *"The model call failed"* | Check the key, the model name, and that your account has credit. The app falls back to the rules engine so nothing is lost. |
| Commentary looks generic | You're in local mode. Add an API key in the sidebar. |
| Dates aren't recognised | Tick *Parse date-like columns* in preprocessing. It only converts columns whose **names** hint at dates (`date`, `time`, `day`, `_at`, `_on`). Rename the column if needed. |

---

## Honest limits

Worth knowing before you circulate anything Baba Jee writes:

- **Descriptive, not inferential.** Nothing here is a significance test. No p-values, no confidence intervals, no hypothesis testing.
- **Pearson correlation only.** It measures *linear* association. Two columns can be perfectly related in a curve and still show r near zero.
- **The model can still be wrong.** It is constrained to the computed profile and told not to invent figures, but model-written prose should be reviewed before it reaches a decision-maker. The tables and numbers are computed in Python and are reliable.
- **Small samples mislead.** Below ~30 rows, treat every statistic as indicative only. The agent flags this.
- **Charts sample large data.** Above 5,000 rows, scatter and line charts draw a random sample for responsiveness. The statistics always use every row.

---

## A five-minute tour

1. Open the app → **Data upload** → **Load sample dataset**.
2. Skim the **Schema** and **First impressions** tabs. Note the empty `Internal Note` column and the 9 duplicate rows.
3. Go to **Data preprocessing**, keep the defaults, press **Run preprocessing**. Watch the audit trail: 11 columns renamed, 9 duplicates removed, 2 junk columns dropped.
4. Go to **Data analysis**, press **Run analysis**. You should find `revenue` and `marketing_spend` correlated around r = 0.96 — and a reminder that this is association, not cause.
5. Go to **Data visualization**. Keep the suggested charts; open a **Why this chart** expander.
6. Go to **Final report**, press **Generate report**, download the markdown.

That's the whole agent.
