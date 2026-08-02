"""Streamlit entry point for deckforge."""

import streamlit as st

from state import init_state

st.set_page_config(page_title="deckforge", layout="wide")

init_state()

st.info("**Setup** → Struktur → Deck")  # ponytail: hardcoded phase text, real indicator once phase logic exists (#30+)
st.caption("LLM-Provider: nicht konfiguriert")

sidebar, preview = st.columns([1, 2])

with sidebar:
    st.header("Steuerung")

with preview:
    st.header("Vorschau")
