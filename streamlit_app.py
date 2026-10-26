from __future__ import annotations

import hashlib
import importlib.metadata
import logging
import os
from pathlib import Path
import time

import requests
import streamlit as st

from runtime import FlowRuntime, answer_text


st.set_page_config(page_title="Perplexia", page_icon="✳", layout="centered")
st.markdown("""
<style>
    .block-container { max-width: 820px; padding-top: 3.4rem; }
    h1 { letter-spacing: -0.055em; font-size: 3.5rem !important; font-weight: 650 !important; }
    [data-testid="stCaptionContainer"] { color: #68716B; }
    .stButton button, .stFormSubmitButton button { border-radius: 7px; }
    textarea { line-height: 1.6 !important; }
</style>
""", unsafe_allow_html=True)

st.caption("LEVELUP LABS / LANGFLOW DEPLOYMENT DEMO")
st.title("Perplexia")
st.write("Ask a question. Get a clear answer.")


def secret(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except st.errors.StreamlitSecretNotFoundError:
        return ""


@st.cache_resource(show_spinner=False)
def get_runtime(flow_digest: str, _api_key: str) -> FlowRuntime:
    return FlowRuntime(Path(__file__).parent / "flows" / "perplexia.json", _api_key)


api_key = secret("OPENAI_API_KEY")
if not api_key:
    st.info("The app is deployed. Add OPENAI_API_KEY in the app's Secrets to enable answers.")

with st.form("question_form"):
    question = st.text_area(
        "Your question", placeholder="What is MCP? Explain it with a practical example.",
        height=120, max_chars=2000,
    )
    submitted = st.form_submit_button("Ask Perplexia", type="primary", disabled=not api_key)

if submitted:
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        try:
            started = time.monotonic()
            with st.spinner("Working on your answer…"):
                flow_path = Path(__file__).parent / "flows" / "perplexia.json"
                digest = hashlib.sha256(flow_path.read_bytes()).hexdigest()
                runtime = get_runtime(digest, api_key)
                payload = runtime.ask(question.strip())
                text = answer_text(payload)
            st.session_state["last_answer"] = {
                "question": question.strip(), "text": text,
                "seconds": time.monotonic() - started,
                "flow_id": runtime.flow_id,
            }
        except (RuntimeError, ValueError, requests.RequestException):
            logging.exception("Flow execution failed")
            st.error("The flow could not answer. Check the app's runtime logs and API key, then try again.")

answer = st.session_state.get("last_answer")
if answer:
    st.divider()
    st.caption("ANSWER")
    st.markdown(answer["text"])
    with st.expander("Run details"):
        st.write(f"Completed in {answer['seconds']:.1f} seconds")
        st.write(f"Runtime: LFX {importlib.metadata.version('lfx')}")
        st.write("Flow: Chat Input → Language Model → Chat Output")
        st.code(f"POST /flows/{answer['flow_id']}/run", language="text")

st.caption("Each question starts fresh. This demo does not search the web.")
with st.expander("About this demo"):
    st.write("Built visually in Langflow, exported as JSON, and executed by LFX. "
             "Streamlit calls the flow over a private, authenticated HTTP connection. "
             "The Langflow editor is not running in this deployment.")
    st.download_button("Download the Langflow flow", data=(Path(__file__).parent / "flows" / "perplexia.json").read_bytes(),
                       file_name="perplexia.json", mime="application/json")
