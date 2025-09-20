"""Float comparison page."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

if __package__ in {None, ""}:
    current_dir = Path(__file__).resolve().parent
    for parent in (current_dir, *current_dir.parents):
        if (parent / "app").is_dir():
            sys.path.insert(0, str(parent))
            break

from app.app_layout import run_data_interface
from app.navigation import render_header

st.set_page_config(page_title="🌊 FloatChat AI — Float Comparison", layout="wide")

render_header("Float Comparison")
run_data_interface("Float Comparison")
