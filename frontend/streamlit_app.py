import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="DocChat Cloud", page_icon="💬")
st.title("DocChat Cloud 💬")
st.caption("Agentic RAG chat over your documents — running on Azure.")

with st.sidebar:
    st.markdown("**API status**")
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        if r.ok:
            st.success("API online")
        else:
            st.error(f"API error: HTTP {r.status_code}")
    except requests.RequestException:
        st.error("API offline")

question = st.text_input("Ask something (e.g. how does the CI/CD of this project work?)")
if st.button("Send", type="primary") and question:
    try:
        with st.spinner("The agent is thinking (triage → answer → verify)..."):
            r = requests.post(
                f"{API_URL}/api/chat", json={"question": question}, timeout=120
            )
        r.raise_for_status()
        data = r.json()
        st.markdown(data["answer"])
        if data.get("verification"):
            with st.expander("🔍 Verification report"):
                st.text(data["verification"])
                st.caption(f"Model: {data.get('model', '?')}")
    except requests.RequestException as exc:
        st.error(f"Request failed: {exc}")
