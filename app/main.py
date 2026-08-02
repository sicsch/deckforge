"""Streamlit entry point for deckforge."""

import os

import streamlit as st
from dotenv import load_dotenv
from phases import render_phase_indicator, render_preview, render_sidebar
from state import init_state

load_dotenv()

st.set_page_config(page_title="deckforge", layout="wide")

init_state()

render_phase_indicator()
st.caption(f"LLM-Provider: {os.getenv('LLM_PROVIDER', 'azure')}")

sidebar, preview = st.columns([1, 2])

with sidebar:
    st.header("Steuerung")
    render_sidebar()

with preview:
    st.header("Vorschau")
    render_preview()
