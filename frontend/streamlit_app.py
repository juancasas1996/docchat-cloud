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

question = st.text_input("Ask something")
if st.button("Send", type="primary") and question:
    try:
        r = requests.post(
            f"{API_URL}/api/chat", json={"question": question}, timeout=30
        )
        r.raise_for_status()
        st.markdown(r.json()["answer"])
    except requests.RequestException as exc:
        st.error(f"Request failed: {exc}")
