"""Plotly map page."""
import streamlit as st

from app.app_layout import run_data_interface
from app.navigation import render_header

st.set_page_config(page_title="🌊 FloatChat AI — Plotly Map", layout="wide")

map_choice = render_header("Maps", current_map="Plotly")
run_data_interface("Maps", map_choice or "Plotly")
