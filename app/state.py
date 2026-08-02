"""Session-state initialization for deckforge's Streamlit app."""

import streamlit as st

DEFAULT_STATE = {
    "phase": "setup",
    "guideline_md": None,
    "guideline_name": None,
    "setup": {
        "thema": "",
        "zielgruppe": "",
        "ziel": "",
        "wirkung": "",
        "rohinhalte": "",
    },
    "structure_md": None,
    "structure_version": 0,
    "structure_chat": [],
    "deck_html": None,
    "deck_chat": [],
    "deck_history": [],
    "confirm_back_to_structure": False,
    "error": None,
}


def init_state() -> None:
    """Populate st.session_state with default keys.

    Does not overwrite keys already present.
    """
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value
