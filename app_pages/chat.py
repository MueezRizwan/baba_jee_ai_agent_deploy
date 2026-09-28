"""Ask Baba Jee — a grounded conversation about the loaded dataset."""

from __future__ import annotations

import streamlit as st

from agent import llm, qa
from agent.analysis import analyse, build_prompt
from agent.profiling import as_prompt, profile
from agent.state import active_df
from agent.ui import page_header

page_header(
    "Ask Baba Jee",
    "Questions are answered from the computed profile of your dataset — not from memory, and not from guesswork.",
    eyebrow="Conversation",
)

df = active_df()

if df is None:
    st.info("Load a dataset first and Baba Jee will answer questions about it.", icon=":material/upload_file:")
    if st.button("Go to data upload", icon=":material/arrow_outward:", type="primary"):
        st.switch_page("app_pages/upload.py")
    st.stop()

context = st.session_state.analysis or analyse(df, st.session_state.source_name)
ready = llm.is_ready()

with st.container(horizontal=True, vertical_alignment="center"):
    st.caption(f"Context: `{st.session_state.source_name}` · {len(df):,} rows · {df.shape[1]} columns")
    if ready:
        st.badge(f"Model · {st.session_state.model}", icon=":material/bolt:", color="green")
    else:
        st.badge("Local mode · rule-based answers", icon=":material/offline_bolt:", color="orange")

SUGGESTIONS = {
    ":blue[:material/help:] Where should I start?": qa.SUGGESTION_TEXT["first"],
    ":green[:material/query_stats:] Explain the correlations": qa.SUGGESTION_TEXT["correlations"],
    ":orange[:material/warning:] What could go wrong?": qa.SUGGESTION_TEXT["risks"],
    ":violet[:material/lightbulb:] Suggest questions to ask": qa.SUGGESTION_TEXT["questions"],
    ":gray[:material/dataset:] Describe the dataset": "Give me an overview of this dataset.",
    ":red[:material/scatter_plot:] Any outliers?": "Which columns have outliers?",
}

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = None
if not st.session_state.messages:
    picked = st.pills("Try asking", list(SUGGESTIONS), label_visibility="collapsed")
    if picked:
        prompt = SUGGESTIONS[picked]
    st.caption(
        "Pick a starter above, or type your own question — naming a column works well, for example "
        "*\"tell me about revenue\"*."
    )

typed = st.chat_input("Ask about this dataset", submit_mode="disable")
prompt = typed or prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status(":shimmer[Consulting the dataset profile]", type="compact") as status:
            with st.status("Loading the computed profile", type="step"):
                st.write(f"{context['profile']['n_columns']} columns, {context['profile']['rows']:,} rows.")
            with st.status("Grounding the answer", type="step"):
                st.write(
                    f"{len(context['corr_pairs'])} correlation(s) and "
                    f"{len(context['outliers'])} outlier column(s) in scope."
                )
            status.update(label="Context assembled", state="complete")

        if ready:
            history = st.session_state.messages[-8:-1]
            try:
                answer = st.write_stream(llm.stream(build_prompt(context, prompt), history=history))
            except RuntimeError as exc:
                st.warning(f"{exc} — answering from the statistics engine instead.", icon=":material/warning:")
                answer = qa.answer(prompt, context, df)
                st.markdown(answer)
        else:
            answer = qa.answer(prompt, context, df)
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()

if st.session_state.messages:
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Clear conversation", icon=":material/delete_sweep:"):
            st.session_state.messages = []
            st.rerun()

if not ready:
    st.caption(
        "Baba Jee is answering from the statistics he computed, so every figure is real — but he can only "
        "handle questions those statistics cover. Add an OpenAI key in the sidebar for open-ended conversation."
    )

with st.expander("What Baba Jee can see", icon=":material/visibility:"):
    st.caption(
        "Only this profile is sent to the model — aggregate statistics, never your raw rows. "
        "That keeps the request small and keeps record-level data in your session."
    )
    st.json(as_prompt(profile(df, st.session_state.source_name)), expanded=False)
