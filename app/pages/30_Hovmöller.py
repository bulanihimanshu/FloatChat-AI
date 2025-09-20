"""Hovmöller diagnostics page."""
import streamlit as st

from app.app_layout import run_data_interface
from app.navigation import render_header

st.set_page_config(page_title="🌊 FloatChat AI — Hovmöller", layout="wide")

render_header("Hovmöller")
run_data_interface("Hovmöller")
