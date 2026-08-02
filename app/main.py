"""Streamlit entry point for deckforge."""

import streamlit as st

st.set_page_config(page_title="deckforge", layout="wide")

st.info("Phase: **Setup**")
st.caption("LLM-Provider: nicht konfiguriert")

sidebar, preview = st.columns([1, 2])

with sidebar:
    st.header("Steuerung")

with preview:
    st.header("Vorschau")
